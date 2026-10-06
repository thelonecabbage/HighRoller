import * as hmUI from "@zos/ui";
import { onGesture, GESTURE_LEFT, GESTURE_RIGHT, GESTURE_UP } from "@zos/interaction";
import { log as Logger } from "@zos/utils";
import {
  DICE,
  MAX_ROLLS,
  dieAnimStyle,
  rollStyle,
  sumPillStyle,
  sumTextStyle,
} from "zosLoader:./index.page.[pf].layout.js";

const logger = Logger.getLogger("high-roller");

let dieIndex = 0;
let rolls = []; // { value, color }
let dieWidget = null;
let ringWidgets = [];

function clearWidgets(list) {
  list.forEach((w) => hmUI.deleteWidget(w));
  list.length = 0;
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

function showDie() {
  if (dieWidget) hmUI.deleteWidget(dieWidget);
  const die = DICE[dieIndex];
  dieWidget = hmUI.createWidget(hmUI.widget.IMG_ANIM, dieAnimStyle(die.name));
  dieWidget.setProperty(hmUI.prop.ANIM_STATUS, hmUI.anim_status.START);
  dieWidget.addEventListener(hmUI.event.CLICK_UP, () => recordRoll(die));
}

function cycleDie(step) {
  dieIndex = (dieIndex + step + DICE.length) % DICE.length;
  showDie();
}

Page({
  onInit() {
    logger.debug("page onInit invoked");
    dieIndex = 0;
    rolls = [];
    dieWidget = null;
    ringWidgets = [];
  },
  build() {
    logger.debug("page build invoked");
    showDie();
    // Returning true suppresses the default swipe (swipe right would otherwise exit the app).
    onGesture({
      callback: (event) => {
        if (event === GESTURE_LEFT) cycleDie(1);
        else if (event === GESTURE_RIGHT) cycleDie(-1);
        else if (event === GESTURE_UP) clearRolls();
        else return false;
        return true;
      },
    });
  },
  onDestroy() {
    logger.debug("page onDestroy invoked");
  },
});
