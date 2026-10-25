# SPDX-License-Identifier: GPL-3.0-or-later
"""A scalable controller reference, shared by the Tk canvas and SVG export."""
import xml.etree.ElementTree as ET


BG = "#111a23"
CARD = "#182430"
LINE = "#344755"
TEXT = "#e9f0f4"
MUTED = "#a5b7c4"
ACCENT = "#efb55b"
TEAL = "#78d4bf"
WIDTH, HEIGHT = 1120, 454


class Scene:
    def __init__(self):
        self.items = []

    def add(self, kind, **attrs):
        self.items.append((kind, attrs))

    def rect(self, x, y, width, height, fill, stroke="none", radius=0):
        self.add("rect", x=x, y=y, width=width, height=height, fill=fill, stroke=stroke, rx=radius)

    def circle(self, x, y, radius, fill, stroke="none"):
        self.add("circle", cx=x, cy=y, r=radius, fill=fill, stroke=stroke)

    def line(self, points, stroke=LINE, width=1.5):
        self.add("polyline", points=points, fill="none", stroke=stroke, stroke_width=width)

    def polygon(self, points, fill, stroke=LINE):
        self.add("polygon", points=points, fill=fill, stroke=stroke)

    def text(self, x, y, text, size=16, fill=TEXT, anchor="start", bold=False):
        self.add("text", x=x, y=y, text=text, font_size=size, fill=fill,
                 text_anchor=anchor, font_weight="bold" if bold else "normal")

    def svg(self):
        ET.register_namespace("", "http://www.w3.org/2000/svg")
        root = ET.Element("{http://www.w3.org/2000/svg}svg", {
            "viewBox": f"0 0 {WIDTH} {HEIGHT}", "width": str(WIDTH), "height": str(HEIGHT),
            "role": "img", "aria-labelledby": "title description",
            "font-family": "Noto Sans, DejaVu Sans, sans-serif",
        })
        ET.SubElement(root, "title", id="title").text = "Crusader: No Remorse controller layout"
        ET.SubElement(root, "desc", id="description").text = (
            "Xbox-style gamepad with a separate label for every mapped button and D-pad direction.")
        for kind, values in self.items:
            attrs = {key.replace("_", "-"): str(value) for key, value in values.items()
                     if key not in ("text", "points")}
            if kind in ("polyline", "polygon"):
                attrs["points"] = " ".join(f"{x},{y}" for x, y in values["points"])
                attrs["stroke-linejoin"] = "round"
                attrs["stroke-linecap"] = "round"
            if kind == "text":
                attrs["dominant-baseline"] = "central"
            node = ET.SubElement(root, kind, attrs)
            if kind == "text":
                node.text = values["text"]
        return ET.tostring(root, encoding="unicode", xml_declaration=True) + "\n"

    def draw(self, canvas):
        canvas.delete("all")
        width, height = canvas.winfo_width(), canvas.winfo_height()
        scale = min(width / WIDTH, height / HEIGHT)
        dx, dy = (width - WIDTH * scale) / 2, (height - HEIGHT * scale) / 2

        def xy(x, y):
            return dx + x * scale, dy + y * scale

        for kind, item in self.items:
            fill = "" if item.get("fill") == "none" else item.get("fill", "")
            stroke = "" if item.get("stroke") == "none" else item.get("stroke", "")
            if kind == "rect":
                x, y = xy(item["x"], item["y"])
                w, h = item["width"] * scale, item["height"] * scale
                r = item["rx"] * scale
                if r:
                    points = [x+r, y, x+w-r, y, x+w, y, x+w, y+r, x+w, y+h-r,
                              x+w, y+h, x+w-r, y+h, x+r, y+h, x, y+h, x, y+h-r, x, y+r, x, y]
                    canvas.create_polygon(points, smooth=True, fill=fill, outline=stroke, width=scale)
                else:
                    canvas.create_rectangle(x, y, x+w, y+h, fill=fill, outline=stroke, width=scale)
            elif kind == "circle":
                x, y = xy(item["cx"], item["cy"])
                r = item["r"] * scale
                canvas.create_oval(x-r, y-r, x+r, y+r, fill=fill, outline=stroke, width=scale)
            elif kind == "polyline":
                points = [number for point in item["points"] for number in xy(*point)]
                canvas.create_line(points, fill=stroke, width=item["stroke_width"] * scale,
                                   capstyle="round", joinstyle="round")
            elif kind == "polygon":
                points = [number for point in item["points"] for number in xy(*point)]
                canvas.create_polygon(points, fill=fill, outline=stroke, width=scale)
            elif kind == "text":
                canvas.create_text(*xy(item["x"], item["y"]), text=item["text"], fill=fill,
                                   anchor={"start": "w", "middle": "center", "end": "e"}[item["text_anchor"]],
                                   font=("Noto Sans", -max(11, round(item["font_size"] * scale)), item["font_weight"]))


def controller_scene(labels):
    scene = Scene()
    scene.rect(0, 0, WIDTH, HEIGHT, BG)

    # Sample Bezier curves once so Tk and exported SVG share the same outline.
    def silhouette(start, curves):
        points = [start]
        for control1, control2, end in curves:
            for step in range(1, 17):
                t = step / 16
                u = 1 - t
                points.append(tuple(round(u**3 * start[i] + 3*u*u*t * control1[i] +
                                          3*u*t*t * control2[i] + t**3 * end[i], 2) for i in (0, 1)))
            start = end
        return points

    for x in (386, 649):
        scene.rect(x, 100, 85, 41, "#263847", "#4c616f", 14)
        scene.rect(x+9, 106, 67, 5, "#3a5060", radius=2)
    for x in (371, 651):
        scene.rect(x, 131, 98, 28, "#304452", "#587080", 11)
    outline = silhouette((430, 137), (
        ((470, 127), (650, 127), (690, 137)),
        ((735, 137), (766, 158), (778, 199)),
        ((797, 251), (818, 326), (805, 373)),
        ((800, 393), (784, 405), (766, 401)),
        ((744, 398), (713, 361), (686, 330)),
        ((672, 314), (656, 308), (634, 308)),
        ((596, 308), (524, 308), (486, 308)),
        ((464, 308), (448, 314), (434, 330)),
        ((407, 361), (376, 398), (354, 401)),
        ((336, 405), (320, 393), (315, 373)),
        ((302, 326), (323, 251), (342, 199)),
        ((354, 158), (385, 137), (430, 137)),
    ))
    scene.polygon(outline, "#1b2935", "#506575")
    scene.line([(345, 247), (353, 288), (371, 328), (392, 355)], "#293e4d", 2)
    scene.line([(775, 247), (767, 288), (749, 328), (728, 355)], "#293e4d", 2)
    scene.line([(395, 149), (460, 142)], "#71818b", 2)
    scene.line([(660, 142), (725, 149)], "#71818b", 2)

    scene.circle(560, 175, 17, "#273c48", "#657d8b")
    scene.line([(552, 167), (560, 173), (568, 183)], "#c4d7d9", 2)
    scene.line([(568, 167), (560, 173), (552, 183)], "#c4d7d9", 2)
    scene.text(560, 247, "CRUSADER", 11, "#6c8392", "middle", True)

    for x, y in ((428, 219), (623, 286)):
        scene.circle(x, y, 32, "#0d1720", "#4c616f")
        scene.circle(x, y, 23, "#293d4b", "#69808e")
        scene.circle(x, y, 17, "#1d2d39", "#3c5261")
    for x in (492, 628):
        scene.circle(x, 209, 11, "#243745", "#506575")
    scene.rect(487, 205, 7, 7, "none", MUTED)
    scene.rect(490, 208, 7, 7, "none", MUTED)
    for y in (205, 209, 213):
        scene.line([(624, y), (632, y)], MUTED, 1)

    for text, x, y, color in (("Y", 696, 191, "#e8c46a"), ("X", 668, 219, "#85b8dd"),
                               ("B", 724, 219, "#e39a96"), ("A", 696, 247, "#91cf9e")):
        scene.circle(x, y, 14, "#0d1720", "#4c616f")
        scene.text(x, y, text, 14, color, "middle", True)
    scene.circle(498, 286, 32, "#0e1821", "#4c616f")
    scene.rect(488, 262, 20, 48, "#2b4050", "#587080", 3)
    scene.rect(474, 276, 48, 20, "#2b4050", "#587080", 3)
    scene.circle(498, 286, 6, "#253846")
    for text, x, y in (("↑", 498, 269), ("↓", 498, 303), ("←", 481, 286), ("→", 515, 286)):
        scene.text(x, y, text, 12, TEAL, "middle", True)

    def description(key):
        if key.startswith("AXES_"):
            prefix = "JOY_" + key[5:] + "_STICK_"
            values = [label for token, names in labels.items() if token.startswith(prefix) for label in names]
        else:
            values = labels.get(key, [])
        return " / ".join(dict.fromkeys(values)) or "Unassigned"

    def label(x, y, button, key, route, tint=ACCENT):
        value = description(key)
        size = 16 if len(value) <= 18 else 13 if len(value) <= 25 else 11
        if x < WIDTH / 2:
            route = [(min(250, x+53+len(value)*size*.6+12), y), *route[1:]]
        scene.line(route, "#587080", 1.3)
        scene.circle(*route[-1], 2.5, tint)
        scene.rect(x, y-13, 42, 26, "#233440", radius=6)
        scene.text(x+21, y, button, 13, tint, "middle", True)
        scene.text(x+53, y, value, size, TEXT if value != "Unassigned" else MUTED)

    label(12, 30, "LT", "JOY_LEFT_TRIGGER", [(250, 30), (387, 30), (428, 111)])
    label(12, 72, "LB", "JOY_LEFT_SHOULDER", [(250, 72), (340, 72), (399, 148)])
    label(12, 154, "LS", "AXES_LEFT", [(250, 154), (351, 154), (405, 197)])
    label(12, 196, "L3", "JOY_LEFT_STICK", [(250, 196), (350, 196), (428, 219)])
    label(12, 254, "↑", "JOY_UP", [(250, 254), (278, 254), (278, 251), (470, 251), (498, 269)], TEAL)
    label(12, 296, "←", "JOY_LEFT", [(250, 296), (276, 296), (276, 286), (481, 286)], TEAL)
    label(12, 338, "↓", "JOY_DOWN", [(250, 338), (461, 338), (498, 303)], TEAL)
    label(12, 380, "→", "JOY_RIGHT", [(250, 380), (530, 380), (530, 286), (515, 286)], TEAL)

    label(904, 30, "RT", "JOY_RIGHT_TRIGGER", [(899, 30), (733, 30), (692, 111)])
    label(904, 72, "RB", "JOY_RIGHT_SHOULDER", [(899, 72), (780, 72), (721, 148)])
    label(904, 144, "Y", "JOY_Y", [(899, 144), (810, 144), (729, 168), (696, 191)])
    label(904, 186, "B", "JOY_B", [(899, 186), (768, 186), (724, 219)])
    label(904, 228, "A", "JOY_A", [(899, 228), (778, 247), (696, 247)])
    label(904, 270, "X", "JOY_X", [(899, 270), (768, 270), (650, 260), (650, 219), (668, 219)])
    label(904, 348, "R3", "JOY_RIGHT_STICK", [(899, 348), (680, 348), (623, 286)])
    label(904, 390, "RS", "AXES_RIGHT", [(899, 390), (680, 390), (604, 308)])

    for x, button, key, target in ((493, "View", "JOY_BACK", (492, 209)),
                                  (627, "Menu", "JOY_START", (628, 209))):
        scene.text(x, 30, button, 12, ACCENT, "middle", True)
        scene.text(x, 51, description(key), 15, TEXT, "middle")
        scene.line([(x, 69), target], "#587080", 1.3)
        scene.circle(*target, 2.5, ACCENT)
    scene.text(560, 433, "LS / RS = stick movement     ·     L3 / R3 = stick click", 13, MUTED, "middle")
    return scene
