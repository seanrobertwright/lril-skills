(function () {
  'use strict';

  var body = document.body;
  var storeKey = 'help-me:' + (body.getAttribute('data-slug') || 'checklist');
  var listTitle = body.getAttribute('data-title') || 'the checklist';
  var steps = Array.prototype.slice.call(document.querySelectorAll('.step'));
  var progress = document.getElementById('progress');
  var progressText = document.getElementById('progress-text');
  var doneBox = document.getElementById('done');
  var toast = document.getElementById('toast');
  var toastTimer = null;

  /* ---- remembering ticks (browser storage can be switched off, so never rely on it) */

  function load() {
    try {
      var parsed = JSON.parse(window.localStorage.getItem(storeKey) || '{}');
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
    } catch (e) {
      return {};
    }
  }

  function save() {
    var state = {};
    steps.forEach(function (step) {
      if (tickOf(step).checked) state[step.getAttribute('data-key')] = true;
    });
    try { window.localStorage.setItem(storeKey, JSON.stringify(state)); } catch (e) { /* page still works */ }
  }

  function tickOf(step) { return step.querySelector('.tick'); }

  function refresh() {
    var done = 0;
    var current = null;
    steps.forEach(function (step) {
      var checked = tickOf(step).checked;
      step.classList.toggle('is-done', checked);
      step.classList.remove('current');
      if (checked) done += 1;
      else if (!current) current = step;
    });
    if (current) current.classList.add('current');
    progress.value = done;
    progressText.textContent = done + ' of ' + steps.length + ' done';
    doneBox.hidden = done !== steps.length;
  }

  /* ---- copying */

  function say(message) {
    toast.textContent = message;
    toast.classList.add('show');
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(function () { toast.classList.remove('show'); }, 4000);
  }

  function legacyCopy(text) {
    var area = document.createElement('textarea');
    area.value = text;
    area.setAttribute('readonly', '');
    area.setAttribute('aria-hidden', 'true');
    area.className = 'toast';
    document.body.appendChild(area);
    area.select();
    var ok = false;
    try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    document.body.removeChild(area);
    return ok;
  }

  function copy(text, okMessage) {
    var failed = 'Could not copy automatically. Select the text and press Ctrl+C (Cmd+C on a Mac).';
    function fallback() { say(legacyCopy(text) ? okMessage : failed); }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { say(okMessage); }, fallback);
    } else {
      fallback();
    }
  }

  /* ---- wiring */

  var saved = load();
  steps.forEach(function (step) {
    var tick = tickOf(step);
    if (Object.prototype.hasOwnProperty.call(saved, step.getAttribute('data-key'))) tick.checked = true;
    tick.addEventListener('change', function () { save(); refresh(); });

    // Escape puts the "why" note away until the pointer or focus leaves the step
    step.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') step.classList.add('why-off');
    });
    step.addEventListener('mouseleave', function () { step.classList.remove('why-off'); });
    step.addEventListener('focusout', function (event) {
      if (!step.contains(event.relatedTarget)) step.classList.remove('why-off');
    });

    var n = step.getAttribute('data-n');
    var title = step.getAttribute('data-title');
    step.querySelector('.stuck-btn').addEventListener('click', function () {
      copy(
        'I\'m stuck on step ' + n + ' ("' + title + '") of the help-me checklist "' + listTitle + '". '
          + 'Here is what I did and what I see instead: ',
        'Copied. Paste it into Claude and add what you see on your screen.'
      );
    });
  });

  Array.prototype.forEach.call(document.querySelectorAll('.copy-btn[data-copy]'), function (button) {
    button.addEventListener('click', function () {
      var source = document.getElementById(button.getAttribute('data-copy'));
      if (source) copy(source.textContent, 'Copied. Now paste it where the step says.');
    });
  });

  document.getElementById('done-btn').addEventListener('click', function () {
    copy(
      'I have finished every step of the help-me checklist "' + listTitle + '". Please check that it worked.',
      'Copied. Paste it into Claude.'
    );
  });

  document.getElementById('reset-btn').addEventListener('click', function () {
    steps.forEach(function (step) { tickOf(step).checked = false; });
    save();
    refresh();
    say('Every step is unticked.');
  });

  refresh();
}());
