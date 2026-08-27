import json
import pathlib
import re
import sys

from py_mini_racer import py_mini_racer


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
INDEX_HTML = REPO_ROOT / "index.html"
OPERATORS_JSON = REPO_ROOT / "assets" / "ak" / "data" / "operators.json"


def extract_inline_script(html_text: str) -> str:
    scripts = re.findall(r"<script(?:[^>]*)>(.*?)</script>", html_text, re.S | re.I)
    for script in reversed(scripts):
        if "class TournamentSorter" in script:
            return re.sub(r"(?m)^\s*init\(\);\s*$", "", script)
    raise RuntimeError("Could not find inline sorter script in index.html")


PRELUDE = r"""
var __elements = {};
var __lastSection = '';

function __makeClassList() {
  return {
    add: function() {},
    remove: function() {},
    toggle: function() {}
  };
}

function __makeElement(id) {
  return {
    id: id,
    textContent: '',
    innerHTML: '',
    disabled: false,
    checked: false,
    value: '',
    src: '',
    alt: '',
    loading: '',
    decoding: '',
    className: '',
    dataset: {},
    style: { display: '', width: '' },
    classList: __makeClassList(),
    appendChild: function(child) { return child; },
    removeChild: function() {},
    addEventListener: function() {},
    removeEventListener: function() {},
    click: function() {},
    insertBefore: function(child) { return child; },
    contains: function() { return false; },
    querySelectorAll: function() { return []; },
    querySelector: function() { return __makeElement(id + ':query'); },
    getBoundingClientRect: function() {
      return { top: 0, bottom: 0, left: 0, right: 0, width: 0, height: 0 };
    },
    getContext: function() {
      return {
        fillStyle: '',
        fillRect: function() {}
      };
    },
    toDataURL: function() { return 'data:image/png;base64,'; }
  };
}

var document = {
  documentElement: { clientWidth: 1200 },
  head: { appendChild: function() {} },
  body: { appendChild: function() {}, removeChild: function() {} },
  getElementById: function(id) {
    if (!__elements[id]) __elements[id] = __makeElement(id);
    return __elements[id];
  },
  querySelectorAll: function() { return []; },
  querySelector: function(sel) { return this.getElementById(sel); },
  createElement: function(tag) { return __makeElement(tag); },
  createTextNode: function(text) { return { textContent: text }; }
};

var window = {
  innerWidth: 1200,
  location: { href: 'http://localhost/index.html' },
  scrollTo: function() {}
};

var localStorage = {
  __store: {},
  getItem: function(k) {
    return Object.prototype.hasOwnProperty.call(this.__store, k) ? this.__store[k] : null;
  },
  setItem: function(k, v) {
    this.__store[k] = String(v);
  },
  removeItem: function(k) {
    delete this.__store[k];
  }
};

var URL = {
  createObjectURL: function() { return 'blob:fake'; },
  revokeObjectURL: function() {}
};

function Blob() {}
function FileReader() {}
function alert() {}
function confirm() { return true; }
function fetch() {
  return {
    then: function() { return this; },
    catch: function() { return this; }
  };
}

var console = {
  log: function() {},
  error: function() {}
};

function html2canvas() {
  return {
    then: function(cb) {
      if (cb) cb({ toDataURL: function() { return ''; } });
      return {
        catch: function() {}
      };
    }
  };
}
"""


TEST_HELPERS = r"""
renderResults = function() {};
showSection = function(sectionId) { __lastSection = sectionId; };

function __assert(condition, message) {
  if (!condition) throw new Error(message);
}

function __ids(list) {
  return (list || []).map(function(op) { return op.id; });
}

function __countId(list, id) {
  return list.filter(function(v) { return v === id; }).length;
}

function __flattenItemIds(items, out) {
  out = out || [];
  (items || []).forEach(function(item) {
    out.push(item.op.id);
    __flattenItemIds(item.children, out);
  });
  return out;
}

function __domPairIds() {
  return {
    left: document.getElementById('sortNameLeft').textContent,
    right: document.getElementById('sortNameRight').textContent
  };
}

function __seedOps(ids) {
  allOperators = ids.map(function(id) {
    return {
      id: id,
      name: id,
      appellation: id,
      star: 6,
      gender: 'female'
    };
  });
  opMap = {};
  allOperators.forEach(function(op) { opMap[op.id] = op; });
  return allOperators;
}

function __leaf(id) {
  return { op: opMap[id], children: [] };
}

function __reset(ids, rankCount) {
  __seedOps(ids);
  sorter = new TournamentSorter(allOperators, rankCount || allOperators.length);
  rankingResults = [];
  tierData = null;
  pinnedTop = [];
  buriedBottom = [];
  postponedPairs = {};
  postponedQueue = [];
  _pendingNormalResults = null;
  _pendingNormalSnapshot = null;
  _unrankedTierOps = [];
  _savedSorterSnapshot = null;
  localStorage.__store = {};
  __lastSection = '';

  [
    'sortNameLeft',
    'sortEnLeft',
    'sortNameRight',
    'sortEnRight',
    'sortStatus',
    'resultTitle',
    'resultMeta',
    'resultSummary'
  ].forEach(function(id) {
    document.getElementById(id).textContent = '';
    document.getElementById(id).innerHTML = '';
  });
  document.getElementById('sortProgressFill').style.width = '0%';
  document.getElementById('btnUndo').disabled = true;
  document.getElementById('btnBackSort').style.display = 'none';
  document.getElementById('currentRankingTable').style.display = 'none';
}

function __setPair(leftId, rightId) {
  var li = sorter.items.findIndex(function(it) { return it.op.id === leftId; });
  var ri = sorter.items.findIndex(function(it) { return it.op.id === rightId; });
  __assert(li >= 0 && ri >= 0, 'Unable to build pair ' + leftId + '/' + rightId);
  sorter.currentPair = { i: li, j: ri };
  updateSortPair({ left: sorter.items[li].op, right: sorter.items[ri].op });
}

function __setResults(ids) {
  sorter.results = ids.map(function(id) { return opMap[id]; });
}

function __setItems(ids) {
  sorter.items = ids.map(function(id) { return __leaf(id); });
}

function __run(name, fn) {
  try {
    fn();
    return { name: name, pass: true };
  } catch (err) {
    return {
      name: name,
      pass: false,
      error: String(err && err.message ? err.message : err)
    };
  }
}

function runSorterRegressionTests() {
  var tests = [];

  tests.push(__run('1. normal undo keeps DOM pair aligned with getCurrentPairOps', function() {
    __reset(['A', 'B', 'C'], 3);
    __setPair('A', 'B');
    sorter.select(true);
    sorter.undo();
    var pair = getCurrentPairOps();
    var dom = __domPairIds();
    __assert(pair && dom.left === pair.left.id, 'left mismatch after undo');
    __assert(pair && dom.right === pair.right.id, 'right mismatch after undo');
  }));

  tests.push(__run('2. normal undo then left-select records DOM-left as winner', function() {
    __reset(['A', 'B', 'C'], 3);
    __setPair('A', 'B');
    sorter.select(true);
    sorter.undo();
    var dom = __domPairIds();
    sorter.select(true);
    var last = sorter.history[sorter.history.length - 1];
    __assert(last.winner.op.id === dom.left, 'winner is not the DOM-left operator');
  }));

  tests.push(__run('3. normal undo then left-pin records DOM-left in pinnedTop', function() {
    __reset(['A', 'B', 'C'], 3);
    __setPair('A', 'B');
    sorter.select(true);
    sorter.undo();
    var dom = __domPairIds();
    pinTop(true);
    __assert(pinnedTop.length === 1, 'pinnedTop did not grow');
    __assert(pinnedTop[0].id === dom.left, 'pinnedTop recorded a non-left operator');
  }));

  tests.push(__run('4. postpone skips current comparison without queue growth and keeps DOM/internal aligned', function() {
    __reset(['A', 'B', 'C', 'D'], 4);
    __setPair('A', 'B');
    var queueBefore = postponedQueue.length;
    postponePair();

    __assert(postponedQueue.length === queueBefore, 'postpone should not add to postponedQueue');
    __assert(sorter.history.length === 0, 'postpone should not record comparison history');
    __assert(sorter.results.length === 0, 'postpone should not lock any result');

    var ids = __flattenItemIds(sorter.items, []);
    __assert(__countId(ids, 'A') === 1, 'A should appear exactly once in sorter.items after postpone');
    __assert(__countId(ids, 'B') === 1, 'B should appear exactly once in sorter.items after postpone');

    var pair = getCurrentPairOps();
    var dom = __domPairIds();
    __assert(pair && dom.left === pair.left.id, 'left mismatch after postpone skip');
    __assert(pair && dom.right === pair.right.id, 'right mismatch after postpone skip');
  }));

  tests.push(__run('5. postpone A/B then bury A keeps the remaining evidence pool', function() {
    __reset(['A', 'B', 'C'], 3);
    __setPair('A', 'B');
    postponePair();

    __setPair('A', 'C');
    buryOp(true);

    __setPair('B', 'C');
    sorter.select(true);
    finishSortEarly();

    var ids = __ids(rankingResults);
    __assert(ids.indexOf('A') === -1, 'A should be excluded from final rankingResults');
    __assert(__ids(buriedBottom).indexOf('A') >= 0, 'A should remain recorded in buriedBottom/excluded list');
    __assert(ids.length === 2, 'rankingResults should contain only non-excluded operators');
  }));

  tests.push(__run('6. postpone A/B then pin A keeps A only in pinned region', function() {
    __reset(['A', 'B', 'C'], 3);
    __setPair('A', 'B');
    postponePair();

    __setPair('A', 'C');
    pinTop(true);

    __setResults(['B', 'C']);
    sorter.items = [];
    sorter.currentPair = null;
    advanceSort();

    var ids = __ids(rankingResults);
    __assert(ids[0] === 'A', 'A is not first in final ranking');
    __assert(__countId(ids, 'A') === 1, 'A appears more than once');
  }));

  tests.push(__run('7. one pinned operator still appears after finishSortEarly', function() {
    __reset(['A', 'B', 'C'], 3);
    __setPair('A', 'B');
    pinTop(true);
    finishSortEarly();
    var ids = __ids(rankingResults);
    __assert(ids.indexOf('A') >= 0, 'pinned operator A is missing from results');
    __assert(__countId(ids, 'A') === 1, 'pinned operator A is duplicated');
  }));

  tests.push(__run('8. unfinished pinned-top final sort preview keeps every pinned operator', function() {
    __reset(['A', 'B', 'C', 'D'], 4);
    pinnedTop = [opMap.A, opMap.B, opMap.C];
    startPinnedTopSort([opMap.D]);
    finishSortEarly();
    var ids = __ids(rankingResults);
    ['A', 'B', 'C'].forEach(function(id) {
      __assert(ids.indexOf(id) >= 0, id + ' is missing from pinned preview');
      __assert(__countId(ids, id) === 1, id + ' is duplicated in pinned preview');
    });
  }));

  tests.push(__run('9. auto-push rollback restores results length and avoids duplicate items', function() {
    __reset(['A', 'B'], 2);
    __setPair('A', 'B');
    sorter.select(true);
    sorter.undo();
    var ids = __flattenItemIds(sorter.items, []);
    __assert(sorter.results.length === 0, 'results did not roll back to the pre-select length');
    __assert(ids.length === 2, 'unexpected item count after rollback');
    __assert(__countId(ids, 'A') === 1 && __countId(ids, 'B') === 1, 'duplicate items remain after rollback');
  }));

  tests.push(__run('10. pinned-top final-sort undo keeps DOM/internal pair aligned', function() {
    __reset(['A', 'B', 'C'], 3);
    pinnedTop = [opMap.A, opMap.B, opMap.C];
    startPinnedTopSort([]);
    __setPair('A', 'B');
    sorter.select(true);
    sorter.undo();
    var pair = getCurrentPairOps();
    var dom = __domPairIds();
    __assert(pair && dom.left === pair.left.id, 'pinned undo left mismatch');
    __assert(pair && dom.right === pair.right.id, 'pinned undo right mismatch');
    sorter.select(true);
    var last = sorter.history[sorter.history.length - 1];
    __assert(last.winner.op.id === dom.left, 'pinned undo left-select recorded the wrong winner');
  }));

  tests.push(__run('11. serialize/deserialize preserves _rlb markers', function() {
    __reset(['A', 'B', 'C'], 3);
    __setPair('A', 'B');
    _selectOrig.call(sorter, true);
    var data = sorter.serialize();
    __assert(data.history.length === 1, 'history did not serialize');
    __assert(data.history[0].rlb === 0, 'serialized history is missing rlb');
    var restored = TournamentSorter.deserialize(data, opMap);
    __assert(restored.history.length === 1, 'history did not deserialize');
    __assert(restored.history[0]._rlb === 0, 'deserialized history is missing _rlb');
  }));


  tests.push(__run('12. full real-roster preference oracle simulation with pinned buried and postponed choices', function() {
    __assert(typeof __REAL_OPERATORS !== 'undefined', 'real operator roster was not injected');
    __assert(__REAL_OPERATORS.length > 50, 'real operator roster is unexpectedly small');

    function uniqIds(ops) {
      var seen = {};
      var out = [];
      (ops || []).forEach(function(op) {
        if (!op || !op.id || seen[op.id]) return;
        seen[op.id] = true;
        out.push(op.id);
      });
      return out;
    }

    function seededShuffle(input, seed) {
      var arr = input.slice();
      var state = seed >>> 0;
      function rnd() {
        state = (state * 1664525 + 1013904223) >>> 0;
        return state / 4294967296;
      }
      for (var i = arr.length - 1; i > 0; i--) {
        var j = Math.floor(rnd() * (i + 1));
        var tmp = arr[i];
        arr[i] = arr[j];
        arr[j] = tmp;
      }
      return arr;
    }

    function setDeterministicMathRandom(seed) {
      var state = seed >>> 0;
      Math.random = function() {
        state = (state * 1103515245 + 12345) >>> 0;
        return state / 4294967296;
      };
    }

    function pairKey(a, b) {
      return [a, b].sort().join('|');
    }

    var ids = uniqIds(__REAL_OPERATORS);
    var preference = seededShuffle(ids, 20260517);

    var pinnedOrder = preference.slice(0, 8);
    var buriedCandidateOrder = preference.slice(preference.length - 8);
    var pinnedSet = {};
    var buriedSet = {};
    pinnedOrder.forEach(function(id) { pinnedSet[id] = true; });
    buriedCandidateOrder.forEach(function(id) { buriedSet[id] = true; });

    var rank = {};
    preference.forEach(function(id, idx) { rank[id] = idx; });

    var postponedOnce = {};
    var postponedKeys = [];
    var buriedActionOrder = [];

    __reset(ids, ids.length);
    setDeterministicMathRandom(987654321);
    advanceSort();

    function assertNoDuplicateLiveState(label) {
      var entries = [];
      var inPinnedFinalSort = !!_pendingNormalResults;

      function add(id, source) {
        if (!id) return;
        entries.push({ id: id, source: source });
      }

      function walk(items, source) {
        (items || []).forEach(function(item) {
          if (!item || !item.op) return;
          add(item.op.id, source);
          walk(item.children, source + '.children');
        });
      }

      if (sorter) {
        walk(sorter.items, 'sorter.items');
        (sorter.results || []).forEach(function(op) {
          add(op.id, 'sorter.results');
        });
      }

      if (!inPinnedFinalSort) {
        (pinnedTop || []).forEach(function(op) {
          add(op.id, 'pinnedTop');
        });
      }

      (buriedBottom || []).forEach(function(op) {
        add(op.id, 'buriedBottom');
      });

      var byId = {};
      entries.forEach(function(e) {
        if (!byId[e.id]) byId[e.id] = [];
        byId[e.id].push(e.source);
      });

      Object.keys(byId).forEach(function(id) {
        var sources = byId[id];
        if (sources.length > 1) {
          throw new Error(label + ': duplicate live id ' + id + ' sources=' + sources.join(','));
        }
      });
    }

    function driveOneStep() {
      if (!sorter.currentPair) {
        advanceSort();
        return true;
      }

      var pair = getCurrentPairOps();
      if (!pair) return false;

      var left = pair.left.id;
      var right = pair.right.id;
      var inPinnedFinalSort = !!_pendingNormalResults;

      var dom = __domPairIds();
      __assert(dom.left === left, 'DOM/internal left mismatch during full oracle simulation');
      __assert(dom.right === right, 'DOM/internal right mismatch during full oracle simulation');

      if (!inPinnedFinalSort) {
        if (pinnedSet[left]) {
          pinTop(true);
          assertNoDuplicateLiveState('after pin left');
          return true;
        }
        if (pinnedSet[right]) {
          pinTop(false);
          assertNoDuplicateLiveState('after pin right');
          return true;
        }

        if (buriedSet[left]) {
          buriedActionOrder.push(left);
          buryOp(true);
          assertNoDuplicateLiveState('after bury left');
          return true;
        }
        if (buriedSet[right]) {
          buriedActionOrder.push(right);
          buryOp(false);
          assertNoDuplicateLiveState('after bury right');
          return true;
        }

        var key = pairKey(left, right);
        if (!postponedOnce[key] && postponedKeys.length < 8) {
          postponedOnce[key] = true;
          postponedKeys.push(key);

          var historyBefore = sorter.history.length;
          var resultsBefore = sorter.results.length;
          var queueBefore = postponedQueue.length;

          postponePair();

          __assert(sorter.history.length === historyBefore, 'postpone should not add history');
          __assert(sorter.results.length === resultsBefore, 'postpone should not add results');
          __assert(postponedQueue.length === queueBefore, 'postpone should not add postponedQueue under skip semantics');
          assertNoDuplicateLiveState('after postpone');
          return true;
        }
      }

      sorter.select(rank[left] < rank[right]);

      // If this select finished the pinned final sorter, finalizeResults()
      // keeps sorter.results alive for return-to-sort while pinnedTop also
      // still exists. That overlap is expected after reaching the result page.
      if (__lastSection !== 'section-result') {
        assertNoDuplicateLiveState('after select');
      }

      return true;
    }

    var guard = 0;
    while (__lastSection !== 'section-result' && guard++ < 20000) {
      driveOneStep();
    }

    __assert(guard < 20000, 'full oracle simulation did not finish');
    __assert(__lastSection === 'section-result', 'full oracle simulation did not reach result section');
    __assert(postponedKeys.length >= 3, 'full oracle simulation did not exercise enough postponed pairs');

    var resultIds = __ids(rankingResults);
    var buriedIds = __ids(buriedBottom);
    var buriedIdSet = {};
    buriedIds.forEach(function(id) { buriedIdSet[id] = true; });

    __assert(resultIds.length === ids.length - buriedIds.length, 'rankingResults length mismatch after excluding buried ids: ' + resultIds.length + ' vs ' + (ids.length - buriedIds.length));
    __assert(resultIds.length === new Set(resultIds).size, 'rankingResults contains duplicate ids');

    var resultSet = {};
    resultIds.forEach(function(id) { resultSet[id] = true; });

    ids.forEach(function(id) {
      if (buriedIdSet[id]) {
        __assert(!resultSet[id], 'excluded/buried id leaked into final ranking: ' + id);
      } else {
        __assert(resultSet[id], 'final ranking is missing non-excluded id ' + id);
      }
    });

    pinnedOrder.forEach(function(id, idx) {
      __assert(resultIds[idx] === id, 'pinned order mismatch at #' + idx + ': expected ' + id + ', got ' + resultIds[idx]);
    });

    __assert(buriedIds.length === buriedActionOrder.length, 'buried action/order length mismatch');

    buriedIds.forEach(function(id, idx) {
      __assert(id === buriedActionOrder[idx], 'buriedBottom action order mismatch at #' + idx);
      __assert(resultIds.indexOf(id) === -1, 'buried/excluded id should not appear in rankingResults: ' + id);
    });

    var pinnedIds = {};
    pinnedOrder.forEach(function(id) { pinnedIds[id] = true; });

    var normalSlice = resultIds.slice(pinnedOrder.length);
    normalSlice.forEach(function(id) {
      __assert(!pinnedIds[id], 'pinned id leaked into normal region: ' + id);
      __assert(!buriedIdSet[id], 'buried id leaked into normal region: ' + id);
    });
  }));

  tests.push(__run('13. burying a compared candidate preserves remaining evidence candidates', function() {
    __reset(['A', 'B', 'C', 'D', 'E'], 5);

    __setPair('A', 'B');
    sorter.select(true);   // A > B

    __setPair('C', 'D');
    sorter.select(true);   // C > D

    __setPair('A', 'C');
    sorter.select(true);   // A > C > D, A also has B

    __setPair('A', 'E');
    buryOp(true);          // Exclude A, but keep B and C>D structure alive

    finishSortEarly();

    var ids = __ids(rankingResults);
    __assert(ids.indexOf('A') === -1, 'buried parent A should be excluded');
    __assert(ids.indexOf('C') >= 0, 'compared child C should remain available for current results');
    __assert(ids.indexOf('D') >= 0, 'C child D should remain available for current results');
    __assert(ids.length >= 2, 'current results lost too much compared subtree after bury');
  }));

  tests.push(__run('14. legacy paused new-operator insertion migrates to evidence candidates', function() {
    __reset(['A', 'B', 'C'], 3);
    var state = {
      sorter: { rankCount: 3, items: [], results: ['A', 'B'], comparisons: 2, history: [] },
      sessionFilter: { selectedStars: [6], selectedGenders: ['female'], selectedRank: 3, mergeAlters: false },
      newOpInsertion: {
        op: 'C', lo: 1, hi: 1, mid: 0,
        history: [{ lo: 0, hi: 2, mid: 1 }, { lo: 0, hi: 1, mid: 0 }]
      }
    };
    sorter = TournamentSorter.deserialize(state.sorter, opMap);
    restoreNewOpMergeState(state);
    restorePendingRankingState(state);
    mergeNewDatabaseOperatorsIntoProgress();
    var ids = sorter.getAllOperators().map(function(op) { return op.id; }).sort();
    __assert(ids.join(',') === 'A,B,C', 'legacy candidate migration failed: ' + ids.join(','));
    __assert(sorter.ledger.records.length === 2, 'paused insertion evidence was lost');
    __assert(sorter.ledger.records[0].w === 'C' && sorter.ledger.records[0].l === 'B', 'first inferred comparison is wrong');
    __assert(sorter.ledger.records[1].w === 'A' && sorter.ledger.records[1].l === 'C', 'second inferred comparison is wrong');
    __assert(!_newOpInsertion && _newOpQueue.length === 0, 'legacy insertion state was not cleared');
  }));

  tests.push(__run('15. pinned final-sort save/restore keeps the original normal snapshot', function() {
    __reset(['A', 'B', 'C'], 3);
    _sessionFilter = { selectedStars: [6], selectedGenders: ['female'], selectedRank: 3, mergeAlters: false };
    var original = snapshotSorter();
    pinnedTop = [opMap.A, opMap.B];
    startPinnedTopSort([opMap.C], original);
    saveProgress();
    var saved = JSON.parse(localStorage.getItem(SAVE_KEY));
    __assert(saved.pendingNormalResults.join(',') === 'C', 'pending normal results were not saved');
    __assert(saved.pendingNormalSnapshot.sorter.items.length === 3, 'original sorter snapshot was not saved');
    __assert(loadProgress(), 'saved pinned phase did not restore');
    __assert(_pendingNormalResults.length === 1 && _pendingNormalResults[0].id === 'C', 'pending normal results were not restored');
    __assert(sorter.getAllOperators().length === 2, 'normal pool was merged into the temporary pinned sorter');
    __assert(!!sorter.getNextPair(), 'pinned pair was not restored');
    sorter.select(true);
    __assert(_savedSorterSnapshot.sorter.items.length === 3, 'original sorter snapshot was replaced by pinned sorter');
    __assert(rankingResults.length === 3, 'final merged ranking lost an operator');
  }));



  return tests;
}
"""


def main() -> int:
    html_text = INDEX_HTML.read_text(encoding="utf-8")
    app_script = extract_inline_script(html_text)

    ctx = py_mini_racer.MiniRacer()
    ctx.eval(PRELUDE)
    ctx.eval(app_script)

    real_ops = [
        op for op in json.loads(OPERATORS_JSON.read_text(encoding="utf-8"))
        if op.get("id")
    ]
    ctx.eval("var __REAL_OPERATORS = " + json.dumps(real_ops, ensure_ascii=False) + ";")

    ctx.eval(TEST_HELPERS)

    raw = ctx.eval("JSON.stringify(runSorterRegressionTests())")
    results = json.loads(raw)

    failed = False
    for result in results:
      status = "PASS" if result["pass"] else "FAIL"
      line = f"{status} {result['name']}"
      if not result["pass"] and result.get("error"):
          line += f" :: {result['error']}"
          failed = True
      print(line)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
