import * as hmUI from "@zos/ui";
import { getDeviceInfo } from "@zos/device";
import { px } from "@zos/utils";

export const { width: DEVICE_WIDTH, height: DEVICE_HEIGHT } = getDeviceInfo();

// Frames are rendered at this fixed pixel size by scripts/render_d6.py and render_dice.py.
export const DIE_SIZE = 200;
const ANIM_FRAMES = 24;
const ANIM_FPS = 17; // frames were rendered for 24 fps; 17 is about 30% slower

export const DICE = [
  { name: "d4", sides: 4, color: 0x28c85a },
  { name: "d6", sides: 6, color: 0x4d8bff },
  { name: "d8", sides: 8, color: 0x9646ff },
  { name: "d10", sides: 10, color: 0xff8c1e },
  { name: "d12", sides: 12, color: 0xf0323c },
  { name: "d20", sides: 20, color: 0x14d2c8 },
];

// Ring slots start at upper-left (45 degrees above the left axis) and run clockwise.
const RING_SLOTS = 12;
const RING_START_BEARING = 315;
const RING_RADIUS = Math.min(DEVICE_WIDTH, DEVICE_HEIGHT) / 2 - px(40);
export const MAX_ROLLS = RING_SLOTS - 1; // the last slot is reserved for the sum

const SLOT_W = px(56);
const SLOT_H = px(40);
const SUM_W = px(76);
const SUM_COLOR = 0xffc107;

export const DIE_X = Math.floor((DEVICE_WIDTH - DIE_SIZE) / 2);
export const DIE_Y = Math.floor((DEVICE_HEIGHT - DIE_SIZE) / 2);

export function dieAnimStyle(name, x = DIE_X, y = DIE_Y) {
  return {
    x,
    y,
    w: DIE_SIZE,
    h: DIE_SIZE,
    anim_path: `anim/${name}`,
    anim_prefix: name,
    anim_ext: "png",
    anim_fps: ANIM_FPS,
    anim_size: ANIM_FRAMES,
    repeat_count: 0,
  };
}

// Near-invisible full-screen rect that receives all touch events.
export function hitAreaStyle() {
  return { x: 0, y: 0, w: DEVICE_WIDTH, h: DEVICE_HEIGHT, color: 0x000000, alpha: 1 };
}

function slotCentre(slot) {
  const rad = ((RING_START_BEARING + (slot * 360) / RING_SLOTS) * Math.PI) / 180;
  return {
    cx: DEVICE_WIDTH / 2 + RING_RADIUS * Math.sin(rad),
    cy: DEVICE_HEIGHT / 2 - RING_RADIUS * Math.cos(rad),
  };
}

function textStyle(slot, w, text, color) {
  const { cx, cy } = slotCentre(slot);
  return {
    x: Math.round(cx - w / 2),
    y: Math.round(cy - SLOT_H / 2),
    w,
    h: SLOT_H,
    text,
    color,
    text_size: px(30),
    align_h: hmUI.align.CENTER_H,
    align_v: hmUI.align.CENTER_V,
  };
}

export function rollStyle(slot, value, color) {
  return textStyle(slot, SLOT_W, String(value), color);
}

export function sumPillStyle(slot) {
  const { cx, cy } = slotCentre(slot);
  return {
    x: Math.round(cx - SUM_W / 2),
    y: Math.round(cy - SLOT_H / 2),
    w: SUM_W,
    h: SLOT_H,
    radius: SLOT_H / 2,
    color: SUM_COLOR,
  };
}

export function sumTextStyle(slot, sum) {
  return textStyle(slot, SUM_W, `+${sum}`, 0x000000);
}
