import json
import pathlib
import re
import sys

from py_mini_racer import py_mini_racer


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
INDEX_HTML = REPO_ROOT / "index.html"


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

  tests.push(__run('5. postpone A/B then bury A leaves A only in buried region', function() {
    __reset(['A', 'B', 'C'], 3);
    __setPair('A', 'B');
    postponePair();

    __setPair('A', 'C');
    buryOp(true);

    __setResults(['B', 'C']);
    sorter.items = [];
    sorter.currentPair = null;
    advanceSort();

    var ids = __ids(rankingResults);
    __assert(ids[ids.length - 1] === 'A', 'A is not last in final ranking');
    __assert(__countId(ids, 'A') === 1, 'A appears more than once');
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

  return tests;
}
"""


def main() -> int:
    html_text = INDEX_HTML.read_text(encoding="utf-8")
    app_script = extract_inline_script(html_text)

    ctx = py_mini_racer.MiniRacer()
    ctx.eval(PRELUDE)
    ctx.eval(app_script)
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
