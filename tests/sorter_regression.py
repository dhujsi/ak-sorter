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

  tests.push(__run('7. classic merge mode refuses an incomplete early result without losing a pinned operator', function() {
    __reset(['A', 'B', 'C'], 3);
    __setPair('A', 'B');
    pinTop(true);
    finishSortEarly();
    var ids = __ids(rankingResults);
    __assert(ids.length === 0, 'incomplete classic merge unexpectedly produced a result');
    __assert(__ids(pinnedTop).indexOf('A') >= 0, 'pinned operator A was lost');
  }));

  tests.push(__run('8. classic merge mode refuses an unfinished pinned-top preview', function() {
    __reset(['A', 'B', 'C', 'D'], 4);
    pinnedTop = [opMap.A, opMap.B, opMap.C];
    startPinnedTopSort([opMap.D]);
    finishSortEarly();
    var ids = __ids(rankingResults);
    ['A', 'B', 'C'].forEach(function(id) {
      __assert(ids.indexOf(id) === -1, id + ' unexpectedly appeared in an incomplete result');
      __assert(__ids(pinnedTop).indexOf(id) >= 0, id + ' was lost from pinnedTop');
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
    // This legacy stress test exercises the adaptive evidence path. Reference
    // mode has focused Top-N state-machine coverage in tests 18-20 below.
    sorter.sortingMode = 'layered';
    sorter.comparisonBudget = sorter.items.length * 3;
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
    sorter.sortingMode = 'layered';

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

  tests.push(__run('16. sorting modes share evidence and survive serialization', function() {
    __reset(['A', 'B', 'C'], 2);
    __setPair('A', 'B');
    sorter.select(true);
    var evidenceBefore = JSON.stringify(sorter.ledger.serialize());
    setSortingMode('layered');
    __assert(sorter.sortingMode === 'layered', 'active sorter mode did not switch');
    __assert(JSON.stringify(sorter.ledger.serialize()) === evidenceBefore, 'mode switch mutated evidence');
    var restored = TournamentSorter.deserialize(sorter.serialize(), opMap);
    __assert(restored.sortingMode === 'layered', 'sorting mode did not survive serialization');
    __assert(JSON.stringify(restored.ledger.serialize()) === evidenceBefore, 'restored mode lost evidence');
  }));

  tests.push(__run('17. legacy exports default to reference mode without losing history', function() {
    __reset(['A', 'B'], 2);
    var legacy = {
      rankCount: 2,
      items: [{ o: 'A', c: [] }, { o: 'B', c: [] }],
      comparisons: 1,
      history: [{ w: 'A', l: 'B' }]
    };
    var restored = TournamentSorter.deserialize(legacy, opMap);
    __assert(restored.sortingMode === 'reference', 'legacy export did not use reference mode');
    __assert(restored.ledger.records.length === 1, 'legacy history was not migrated');
    __assert(restored.ledger.records[0].w === 'A' && restored.ledger.records[0].l === 'B', 'legacy evidence changed');
  }));

  tests.push(__run('18. reference mode fully merge-sorts every candidate before returning Top N', function() {
    __reset(['A', 'B', 'C', 'D', 'E', 'F'], 3);
    sorter.sortingMode = 'reference';
    sorter.referenceState = null;
    var rank = { A: 0, B: 1, C: 2, D: 3, E: 4, F: 5 };
    var guard = 0;
    var pair;
    while ((pair = sorter.getNextPair()) && guard++ < 100) {
      var current = getCurrentPairOps();
      sorter.select(rank[current.left.id] < rank[current.right.id]);
    }
    __assert(guard < 100, 'reference scheduler did not terminate');
    __assert(sorter.isComparisonBudgetComplete(), 'reference scheduler did not complete');
    __assert(__ids(sorter.getReferenceTopOperators()).join(',') === 'A,B,C', 'reference Top 3 is wrong');
    __assert(__ids(sorter.getEvidenceRanking()).join(',') === 'A,B,C,D,E,F', 'full merge result is wrong');
    __assert(sorter.referenceState.algorithm === 'manual-merge-sort', 'reference mode is not using manual merge sort');
    __assert(sorter.comparisons <= sorter.getBaseComparisonBudget(), 'merge sort exceeded its worst-case comparisons');
  }));

  tests.push(__run('19. reference mode reuses direct history without Bradley-Terry scoring', function() {
    __reset(['A', 'B', 'C'], 2);
    sorter.sortingMode = 'layered';
    __setPair('A', 'B'); sorter.select(true);
    __setPair('A', 'C'); sorter.select(true);
    __setPair('B', 'C'); sorter.select(true);
    var comparisonsBefore = sorter.comparisons;
    sorter.sortingMode = 'reference';
    sorter.referenceState = null;
    __assert(typeof sorter.ledger.calculateScores === 'undefined', 'Bradley-Terry method still exists');
    var next = sorter.getNextPair();
    __assert(next === null, 'known direct history should finish reference Top 2 without a new question');
    __assert(__ids(sorter.getReferenceTopOperators()).join(',') === 'A,B', 'direct history seeded the wrong Top 2');
    __assert(sorter.comparisons === comparisonsBefore, 'reused history counted as new comparisons');
  }));

  tests.push(__run('20. reference undo reconstructs the same merge pair and removes evidence', function() {
    __reset(['A', 'B', 'C'], 2);
    sorter.sortingMode = 'reference';
    sorter.referenceState = null;
    var pair = sorter.getNextPair();
    __assert(!!pair, 'reference mode did not produce a pair');
    var beforeIds = [pair.left.id, pair.right.id].sort().join('|');
    sorter.select(true);
    __assert(sorter.undo(), 'reference undo failed');
    __assert(sorter.ledger.records.length === 0, 'reference undo left comparison evidence behind');
    sorter.currentPair = null;
    var replayed = sorter.getNextPair();
    __assert(!!replayed, 'reference undo did not reconstruct a merge pair');
    __assert([replayed.left.id, replayed.right.id].sort().join('|') === beforeIds, 'reference undo reconstructed a different merge pair');
  }));

  tests.push(__run('21. partial transitional evidence merges with legacy history without duplicates', function() {
    __reset(['A', 'B', 'C'], 3);
    var history = [
      { w: 'A', l: 'B' },
      { w: 'B', l: 'C' },
      { w: 'A', l: 'B' }
    ];
    var ledger = ComparisonLedger.fromSerialized({
      records: [
        { w: 'A', l: 'B', o: 'win' },
        { w: 'C', l: 'A', o: 'win' }
      ]
    }, history);
    __assert(ledger.records.length === 4, 'partial evidence/history merge count is wrong');
    __assert(ledger.records[0].w === 'A' && ledger.records[1].w === 'B' && ledger.records[2].w === 'A', 'legacy history order changed');
    __assert(ledger.records[3].w === 'C' && ledger.records[3].l === 'A', 'new-only evidence was not appended');
  }));

  tests.push(__run('22. direct evidence preserves a non-transitive cycle without propagation', function() {
    __reset(['A', 'B', 'C'], 3);
    sorter.ledger.add({ w: 'A', l: 'B' });
    sorter.ledger.add({ w: 'B', l: 'C' });
    sorter.ledger.add({ w: 'C', l: 'A' });
    var analysis = sorter.ledger.analyzeDirectEvidence(allOperators);
    __assert(analysis.pairs.get('A|B').majorityWinner === 'A', 'A>B edge was lost');
    __assert(analysis.pairs.get('B|C').majorityWinner === 'B', 'B>C edge was lost');
    __assert(analysis.pairs.get('A|C').majorityWinner === 'C', 'C>A edge was lost');
    ['A', 'B', 'C'].forEach(function(id) {
      __assert(analysis.stats.get(id).score === 0, 'cycle was falsely propagated into a strength score');
    });
  }));

  tests.push(__run('23. one upset does not inherit the established opponent position', function() {
    __reset(['B', 'A', 'C', 'D', 'X'], 5);
    sorter.ledger.add({ w: 'B', l: 'A' });
    sorter.ledger.add({ w: 'B', l: 'C' });
    sorter.ledger.add({ w: 'B', l: 'D' });
    sorter.ledger.add({ w: 'X', l: 'B' });
    var ranked = sorter.ledger.rankDirect(allOperators).map(function(op) { return op.id; });
    __assert(ranked.indexOf('B') < ranked.indexOf('X'), 'X inherited B position from one upset');
    var pair = sorter.ledger.analyzeDirectEvidence(allOperators).pairs.get('B|X');
    __assert(pair.majorityWinner === 'X', 'the direct X>B upset itself was not preserved');
  }));

  tests.push(__run('24. layered refinement keeps recurring lower-to-front challenges', function() {
    var ids = [];
    for (var i = 0; i < 20; i++) ids.push(String.fromCharCode(65 + i));
    __reset(ids, 5);
    sorter.sortingMode = 'layered';
    sorter.referenceState = null;
    // Give every item four distinct direct opponents so the test starts in
    // refinement rather than baseline coverage.
    for (var j = 0; j < ids.length; j++) {
      sorter.ledger.add({ w: ids[j], l: ids[(j + 1) % ids.length] });
      sorter.ledger.add({ w: ids[j], l: ids[(j + 2) % ids.length] });
    }
    sorter.comparisons = sorter.ledger.records.length;
    sorter.comparisonBudget = sorter.comparisons + 100;
    sorter.layeredState = null;
    var crossLayer = 0;
    for (var step = 0; step < 25; step++) {
      var rankedBefore = sorter.ledger.rankDirect(allOperators);
      var rankById = {};
      rankedBefore.forEach(function(op, index) { rankById[op.id] = index; });
      var next = sorter.getNextPair();
      __assert(!!next, 'layered refinement stopped too early');
      var current = getCurrentPairOps();
      var leftRank = rankById[current.left.id];
      var rightRank = rankById[current.right.id];
      if ((leftRank < 5 && rightRank >= 9) || (rightRank < 5 && leftRank >= 9)) crossLayer += 1;
      sorter.select(current.left.id < current.right.id);
    }
    __assert(crossLayer >= 5, 'lower candidates did not receive recurring front challenges: ' + crossLayer);
  }));

  tests.push(__run('25. layered state survives serialization and undo', function() {
    __reset(['A', 'B', 'C', 'D', 'E', 'F'], 3);
    sorter.sortingMode = 'layered';
    sorter.layeredState = null;
    var pair = sorter.getNextPair();
    __assert(!!pair, 'layered mode did not produce a pair');
    var stateBefore = JSON.stringify(sorter.ensureLayeredState());
    sorter.select(true);
    __assert(sorter.undo(), 'layered undo failed');
    __assert(JSON.stringify(sorter.layeredState) === stateBefore, 'layered stability state was not restored');
    var restored = TournamentSorter.deserialize(sorter.serialize(), opMap);
    __assert(restored.sortingMode === 'layered', 'layered mode was not serialized');
    __assert(JSON.stringify(restored.layeredState) === stateBefore, 'layered state was not serialized');
  }));

  tests.push(__run('26. mode switch configures saved progress before resume without touching evidence', function() {
    __reset(['A', 'B', 'C'], 2);
    sorter.ledger.add({ w: 'A', l: 'B' });
    var saved = {
      sorter: sorter.serialize(),
      sessionFilter: { selectedRank: 2, sortingMode: 'reference' }
    };
    var evidenceBefore = JSON.stringify(saved.sorter.evidence);
    localStorage.setItem(SAVE_KEY, JSON.stringify(saved));
    sorter = null;
    setSortingMode('layered');
    var updated = JSON.parse(localStorage.getItem(SAVE_KEY));
    __assert(updated.sorter.sortingMode === 'layered', 'saved sorter mode did not change before resume');
    __assert(updated.sessionFilter.sortingMode === 'layered', 'saved session mode did not change before resume');
    __assert(JSON.stringify(updated.sorter.evidence) === evidenceBefore, 'saved evidence changed while switching mode');
  }));

  tests.push(__run('27. manual merge state survives serialization at an exact comparison boundary', function() {
    __reset(['A', 'B', 'C', 'D', 'E'], 3);
    var rank = { A: 0, B: 1, C: 2, D: 3, E: 4 };
    for (var i = 0; i < 3; i++) {
      var pair = sorter.getNextPair();
      __assert(!!pair, 'merge sorter ended before the save boundary');
      sorter.select(rank[pair.left.id] < rank[pair.right.id]);
    }
    var saved = sorter.serialize();
    __assert(saved.schemaVersion === 5, 'merge sorter schema version was not bumped');
    var expected = sorter.getNextPair();
    var restored = TournamentSorter.deserialize(saved, opMap);
    var actual = restored.getNextPair();
    __assert(!!expected && !!actual, 'saved merge boundary did not restore a pair');
    __assert(
      [expected.left.id, expected.right.id].sort().join('|') === [actual.left.id, actual.right.id].sort().join('|'),
      'saved merge boundary restored a different pair'
    );
  }));

  tests.push(__run('28. legacy ranked results seed migration and obsolete cutoff state is discarded', function() {
    __reset(['A', 'B', 'C', 'D'], 2);
    var legacy = {
      rankCount: 2,
      results: ['C', 'A'],
      items: [{ o: 'B', c: [{ o: 'D', c: [] }] }],
      history: [{ w: 'C', l: 'A' }],
      referenceState: {
        version: 1,
        target: 2,
        order: ['C', 'A'],
        queue: ['B'],
        discarded: ['D'],
        insertion: null
      }
    };
    var restored = TournamentSorter.deserialize(legacy, opMap);
    var state = restored.ensureReferenceState();
    __assert(state.version === 2 && state.algorithm === 'manual-merge-sort', 'legacy cutoff state was not migrated');
    __assert(state.initialOrder.join(',') === 'C,A,B,D', 'legacy result order was not used as the migration seed');
    __assert(restored.getAllOperators().length === 4, 'legacy migration lost a candidate');
    __assert(restored.ledger.records.length === 1, 'legacy migration lost direct history');
  }));

  tests.push(__run('29. manual merge sort keeps every member of a non-transitive cycle', function() {
    __reset(['A', 'B', 'C'], 3);
    sorter.ledger.add({ w: 'A', l: 'B' });
    sorter.ledger.add({ w: 'B', l: 'C' });
    sorter.ledger.add({ w: 'C', l: 'A' });
    var next = sorter.getNextPair();
    __assert(next === null, 'known cycle should replay without a new comparison');
    var ids = __ids(sorter.getEvidenceRanking());
    __assert(ids.length === 3, 'non-transitive merge result lost a candidate');
    ['A', 'B', 'C'].forEach(function(id) {
      __assert(ids.indexOf(id) >= 0, id + ' disappeared from the merge result');
    });
  }));

  tests.push(__run('32. a newly added operator restarts the merge cursor and keeps old evidence', function() {
    __seedOps(['A', 'B', 'C', 'D']);
    sorter = new TournamentSorter([opMap.A, opMap.B, opMap.C], 3, 'reference');
    var rank = { A: 0, B: 1, C: 2, D: 3 };
    var pair;
    var guard = 0;
    while ((pair = sorter.getNextPair()) && guard++ < 100) {
      sorter.select(rank[pair.left.id] < rank[pair.right.id]);
    }
    __assert(sorter.isComparisonBudgetComplete(), 'initial merge did not complete');
    var oldEvidence = sorter.ledger.records.length;
    __assert(addOperatorsToEvidencePool([opMap.D]) === 1, 'new operator was not added');
    __assert(sorter.ledger.records.length === oldEvidence, 'adding an operator changed old evidence');
    __assert(!sorter.ensureReferenceState().completed, 'new operator kept a falsely completed merge state');

    guard = 0;
    while ((pair = sorter.getNextPair()) && guard++ < 200) {
      sorter.select(rank[pair.left.id] < rank[pair.right.id]);
    }
    __assert(guard < 200, 'merge with a newly added operator did not terminate');
    __assert(sorter.isComparisonBudgetComplete(), 'merge with a newly added operator did not complete');
    __assert(__ids(sorter.getEvidenceRanking()).join(',') === 'A,B,C,D', 'new operator changed the established order incorrectly');
    __assert(sorter.ledger.records.length >= oldEvidence, 'new operator merge lost comparison history');
  }));

  tests.push(__run('33. switching back to classic mode rebuilds an obsolete cursor from shared evidence', function() {
    __reset(['A', 'B', 'C', 'D'], 3);
    sorter.sortingMode = 'layered';
    sorter.ledger.add({ w: 'A', l: 'B' });
    sorter.ledger.add({ w: 'B', l: 'C' });
    sorter.comparisons = sorter.ledger.records.length;
    setSortingMode('reference');
    var state = sorter.ensureReferenceState();
    __assert(state.version === 2 && state.algorithm === 'manual-merge-sort', 'classic cursor was not rebuilt');
    __assert(!state.discarded && !state.queue && !state.insertion, 'obsolete cutoff fields leaked into classic state');
    __assert(sorter.ledger.records.length === 2, 'mode switch changed shared evidence');
    var pair = sorter.getNextPair();
    __assert(!!pair, 'rebuilt classic cursor did not produce a pair');
  }));

  tests.push(__run('30. switching away from and back to classic mode rebuilds stale merge state', function() {
    __reset(['A', 'B', 'C'], 3);
    var first = sorter.getNextPair();
    __assert(!!first, 'classic mode did not initialize a merge pair');
    var oldState = sorter.referenceState;
    sorter.ledger.add({ w: 'A', l: 'B' });
    setSortingMode('layered');
    setSortingMode('reference');
    __assert(sorter.referenceState !== oldState, 'mode switch reused stale merge state');
    __assert(sorter.referenceState.version === 2, 'mode switch did not restore merge state');
    __assert(sorter.referenceState.algorithm === 'manual-merge-sort', 'mode switch restored the wrong algorithm');
  }));

  tests.push(__run('31. newly eligible operators rejoin classic merge sort as fresh leaves', function() {
    __reset(['A', 'B', 'C'], 3);
    _sessionFilter = {
      selectedStars: [6],
      selectedGenders: ['female'],
      selectedRank: 3,
      sortingMode: 'reference',
      mergeAlters: false
    };
    var d = { id: 'D', name: 'D', appellation: 'D', star: 6, gender: 'female' };
    allOperators = allOperators.concat([d]);
    opMap.D = d;
    sorter.ledger.add({ w: 'A', l: 'B' });
    sorter.comparisons = 1;
    sorter.ensureReferenceState();
    var added = mergeNewDatabaseOperatorsIntoProgress();
    __assert(added === 1, 'new eligible operator was not added');
    var state = sorter.ensureReferenceState();
    __assert(state.initialOrder.indexOf('D') >= 0, 'new operator was not put into merge input');
    __assert(state.completed === false, 'adding a new operator left the old completion flag active');

    var rank = { A: 0, B: 1, C: 2, D: 3 };
    var guard = 0;
    var pair;
    while ((pair = sorter.getNextPair()) && guard++ < 100) {
      sorter.select(rank[pair.left.id] < rank[pair.right.id]);
    }
    __assert(guard < 100, 'new operator merge did not terminate');
    __assert(sorter.isComparisonBudgetComplete(), 'new operator merge did not complete');
    __assert(__ids(sorter.getEvidenceRanking()).join(',') === 'A,B,C,D', 'new operator changed the merge result incorrectly');
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
