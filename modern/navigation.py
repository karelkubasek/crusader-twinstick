# SPDX-License-Identifier: GPL-3.0-or-later
"""Controller edge/repeat handling, shared by launcher pages and dialogs."""


class Navigation:
    BUTTONS = {0: "confirm", 1: "back", 9: "previous_page", 10: "next_page"}
    DIRECTIONS = {11: "up", 12: "down", 13: "left", 14: "right"}

    def __init__(self):
        self.context = None
        self.held = set()
        self.direction = None
        self.repeat_at = 0
        self.armed = False

    def update(self, buttons, axes, context, now):
        buttons = set(buttons)
        x, y = axes
        if context != self.context or context is None:
            self.context = context
            self.held = buttons
            self.direction = None
            self.armed = False
            return []
        # Require neutral after a focus/page transition. Held input belongs to
        # the old context, including the press that launched a child process.
        if not self.armed:
            self.held = buttons
            if not buttons and max(abs(x), abs(y)) < 0.35:
                self.armed = True
            return []
        actions = [action for button, action in self.BUTTONS.items() if button in buttons - self.held]
        self.held = buttons
        direction = next((action for button, action in self.DIRECTIONS.items() if button in buttons), None)
        threshold = 0.4 if self.direction else 0.6
        if direction is None and max(abs(x), abs(y)) >= threshold:
            direction = ("left" if x < 0 else "right") if abs(x) > abs(y) else ("up" if y < 0 else "down")
        if direction != self.direction:
            self.direction = direction
            self.repeat_at = now + 0.4
            if direction:
                actions.append(direction)
        elif direction and now >= self.repeat_at:
            actions.append(direction)
            self.repeat_at = now + 0.12
        return actions
