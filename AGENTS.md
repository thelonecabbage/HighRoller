# High Roller

A dice rolling app for D&D, built as a Zepp OS smartwatch app (Zeus CLI). The app lives in `high-roller/`.

## Supported dice

- D4
- D6
- D8
- D10
- D12
- D20

## Behavior

- The selected die spins continuously (looping PNG sequence in an `IMG_ANIM` widget) at 17 fps, about 30% slower than the 24 fps the frames were rendered for.
- Dragging left / right moves the die with the finger; past a threshold it slides off in that direction while the next / previous die scrolls in. No wrap-around: at D4 (drag right) and D20 (drag left) the die bounces back.
- Dragging up / down nudges the die a little in that direction and it springs back on release.
- Tap the die to roll: a random 1..N for the shown die.
- Rolls appear in a ring around the screen edge: 12 slots, 30 degrees apart, starting upper-left (45 degrees above the left axis) and running clockwise. Each value uses its die's color.
- With two or more rolls, a highlighted gold `+<sum>` pill appears in the next slot.
- The ring holds 11 rolls plus the sum; the next roll after that restarts the ring.
- Swipe up clears the ring.
- Touch is handled by a near-invisible full-screen `FILL_RECT` (CLICK_DOWN / MOVE / CLICK_UP), recreated above the die whenever a die is added. The `onGesture` handler only suppresses default swipes, so swiping right does not exit the app.

## Layout

- `page/gt/home/index.page.js`: state, gestures, widgets.
- `page/gt/home/index.page.[r|s].layout.js`: dice list/colors, ring geometry, widget styles. Keep both files identical in exports.
- `assets/gt.[r|s]/anim/<die>/<die>_0..23.png`: 24 frames, 200x200 per die.

## Animation frames

- Generated, not hand-made. Re-run from `high-roller/` (needs Pillow and numpy):
  - `python3 scripts/render_d6.py`: D6 (blue, pips).
  - `python3 scripts/render_dice.py [d4 d8 d10 d12 d20]`: other dice, numbered faces.
- Dice colors: D4 green, D6 blue, D8 purple, D10 orange, D12 red, D20 teal. Keep `COLORS` in `render_dice.py` and `DICE` in the layout files in sync.

## Development

- Run from `high-roller/`: `npx zeus dev` (simulator), `npx zeus build`, `npx zeus preview`.
- See `.github/skills/zepp-os-development/SKILL.md` for Zepp OS conventions.
