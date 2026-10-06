import * as hmUI from "@zos/ui";
import { onGesture } from "@zos/interaction";
import { log as Logger } from "@zos/utils";
import {
  DEVICE_WIDTH,
  DIE_SIZE,
  DIE_X,
  DIE_Y,
  DICE,
  MAX_ROLLS,
  dieAnimStyle,
  hitAreaStyle,
  rollStyle,
  sumPillStyle,
  sumTextStyle,
} from "zosLoader:./index.page.[pf].layout.js";

const logger = Logger.getLogger("high-roller");

const TAP_SLOP = 12; // below this movement a touch is a tap
const SWIPE_X = 70; // horizontal distance that commits to the next/previous die
const SWIPE_UP = 60; // upward distance that clears the rolls
const NUDGE_MAX = 28; // how far the die follows a vertical drag
const RUBBER_MAX = 50; // how far the die follows a drag with no die to switch to
const SLIDE_MS = 240;

let dieIndex = 0;
let rolls = []; // { value, color }
let dieWidget = null;
let hitArea = null;
let ringWidgets = [];
let busy = false; // true while a slide or spring-back is animating
let touch = null; // { x, y, axis, dx, dy }

function clearWidgets(list) {
  list.forEach((w) => hmUI.deleteWidget(w));
  list.length = 0;
}

function animate(widget, prop, from, to, duration, rate, onDone) {
  widget.setProperty(hmUI.prop.ANIM, {
    anim_steps: [
      { anim_prop: prop, anim_from: from, anim_to: to, anim_rate: rate, anim_duration: duration },
    ],
    anim_fps: 30,
    anim_complete_func: onDone || (() => {}),
  });
}

function renderRing() {
  clearWidgets(ringWidgets);
  rolls.forEach(({ value, color }, slot) => {
    ringWidgets.push(hmUI.createWidget(hmUI.widget.TEXT, rollStyle(slot, value, color)));
  });
  if (rolls.length >= 2) {
    const slot = rolls.length;
    const sum = rolls.reduce((total, r) => total + r.value, 0);
    ringWidgets.push(hmUI.createWidget(hmUI.widget.FILL_RECT, sumPillStyle(slot)));
    ringWidgets.push(hmUI.createWidget(hmUI.widget.TEXT, sumTextStyle(slot, sum)));
  }
}

function recordRoll(die) {
  if (rolls.length >= MAX_ROLLS) rolls = [];
  rolls.push({ value: Math.floor(Math.random() * die.sides) + 1, color: die.color });
  renderRing();
}

function clearRolls() {
  rolls = [];
  renderRing();
}

function createDie(index, x) {
  const widget = hmUI.createWidget(hmUI.widget.IMG_ANIM, dieAnimStyle(DICE[index].name, x, DIE_Y));
  widget.setProperty(hmUI.prop.ANIM_STATUS, hmUI.anim_status.START);
  return widget;
}

function canStep(step) {
  const target = dieIndex + step;
  return target >= 0 && target < DICE.length;
}

function clamp(v, max) {
  return Math.max(-max, Math.min(max, v));
}

// Die x offset while dragging; damped when there is no neighbouring die.
function dragOffsetX(dx) {
  return canStep(dx < 0 ? 1 : -1) ? dx : clamp(dx * 0.3, RUBBER_MAX);
}

function inDie(x, y) {
  return x >= DIE_X && x <= DIE_X + DIE_SIZE && y >= DIE_Y && y <= DIE_Y + DIE_SIZE;
}

function settle(prop, from, to, rate) {
  if (from === to) return;
  busy = true;
  animate(dieWidget, prop, from, to, SLIDE_MS, rate, () => {
    busy = false;
  });
}

// Slide the current die off in the swipe direction while the next one scrolls in.
function swapDie(step, fromX) {
  busy = true;
  const outgoing = dieWidget;
  const exitTo = fromX - step * DEVICE_WIDTH;
  const enterFrom = DIE_X + step * DEVICE_WIDTH;
  dieIndex += step;
  dieWidget = createDie(dieIndex, enterFrom);
  animate(outgoing, hmUI.prop.X, fromX, exitTo, SLIDE_MS, "easeout");
  animate(dieWidget, hmUI.prop.X, enterFrom, DIE_X, SLIDE_MS, "easeout", () => {
    hmUI.deleteWidget(outgoing);
    raiseHitArea();
    busy = false;
  });
}

function onDown(info) {
  if (busy) return;
  touch = { x: info.x, y: info.y, axis: null, dx: 0, dy: 0 };
}

function onMove(info) {
  if (!touch || busy) return;
  touch.dx = info.x - touch.x;
  touch.dy = info.y - touch.y;
  if (!touch.axis) {
    if (Math.max(Math.abs(touch.dx), Math.abs(touch.dy)) < TAP_SLOP) return;
    touch.axis = Math.abs(touch.dx) > Math.abs(touch.dy) ? "x" : "y";
  }
  if (touch.axis === "x") {
    dieWidget.setProperty(hmUI.prop.MORE, { x: DIE_X + dragOffsetX(touch.dx) });
  } else {
    dieWidget.setProperty(hmUI.prop.MORE, { y: DIE_Y + clamp(touch.dy * 0.35, NUDGE_MAX) });
  }
}

function onUp() {
  if (!touch) return;
  const t = touch;
  touch = null;
  if (busy) return;
  if (!t.axis) {
    if (inDie(t.x, t.y)) recordRoll(DICE[dieIndex]);
    return;
  }
  if (t.axis === "x") {
    const step = t.dx < 0 ? 1 : -1;
    const from = DIE_X + dragOffsetX(t.dx);
    if (canStep(step) && Math.abs(t.dx) >= SWIPE_X) swapDie(step, from);
    else settle(hmUI.prop.X, from, DIE_X, canStep(step) ? "easeout" : "bounce");
  } else {
    if (t.dy <= -SWIPE_UP) clearRolls();
    settle(hmUI.prop.Y, DIE_Y + clamp(t.dy * 0.35, NUDGE_MAX), DIE_Y, "bounce");
  }
}

// Kept above the die so it receives every touch; recreated whenever a new die is added.
function raiseHitArea() {
  if (hitArea) hmUI.deleteWidget(hitArea);
  hitArea = hmUI.createWidget(hmUI.widget.FILL_RECT, hitAreaStyle());
  hitArea.addEventListener(hmUI.event.CLICK_DOWN, onDown);
  hitArea.addEventListener(hmUI.event.MOVE, onMove);
  hitArea.addEventListener(hmUI.event.CLICK_UP, onUp);
}

Page({
  onInit() {
    logger.debug("page onInit invoked");
    dieIndex = 0;
    rolls = [];
    dieWidget = null;
    hitArea = null;
    ringWidgets = [];
    busy = false;
    touch = null;
  },
  build() {
    logger.debug("page build invoked");
    dieWidget = createDie(dieIndex, DIE_X);
    raiseHitArea();
    // Touch handling drives all navigation; this only suppresses the default swipe (swipe right exits).
    onGesture({ callback: () => true });
  },
  onDestroy() {
    logger.debug("page onDestroy invoked");
  },
});
