"""KiKit framing plugin: rails on the left, right and TOP only.

The bottom edge of the panel is the gold-finger edge: JLCPCB bevels it, so it
stays a bare board edge (no rail, no tab, no V-cut). The top rail is sized so
the panel is at least MIN_H tall (JLCPCB Standard PCBA: each side >= 70 mm).
Arg (KiKit preset "arg"): "<side rail mm>,<top rail min mm>,<space mm>,<min panel height mm>".
"""
from kikit.common import fromMm
from kikit.plugin import FramingPlugin
from kikit.panelize_ui_impl import polygonToSubstrate
from shapely.geometry import box


class SidesAndTopRails(FramingPlugin):
    def __init__(self, preset, userArg):
        super().__init__(preset, userArg)
        side, top, space, minh = (float(v) for v in userArg.split(","))
        self.side, self.top, self.space, self.minh = fromMm(side), fromMm(top), fromMm(space), fromMm(minh)

    def _bbox(self, substrates):
        b = [s.bounds() for s in substrates]
        return min(x[0] for x in b), min(x[1] for x in b), max(x[2] for x in b), max(x[3] for x in b)

    def buildDummyFramingSubstrates(self, substrates):
        # KiCad y grows downward: "top" is miny. No dummy below maxy, so no tab
        # can ever reach the finger edge.
        minx, miny, maxx, maxy = self._bbox(substrates)
        w, s = fromMm(1), self.space
        return [polygonToSubstrate(box(minx - 2 * s - w, miny, minx - 2 * s, maxy)),
                polygonToSubstrate(box(maxx + 2 * s, miny, maxx + 2 * s + w, maxy)),
                polygonToSubstrate(box(minx, miny - 2 * s - w, maxx, miny - 2 * s))]

    def buildFraming(self, panel):
        minx, miny, maxx, maxy = panel.boardsBBox()
        s, side = self.space, self.side
        top = max(self.top, self.minh - (maxy - miny) - s)
        y0 = miny - s - top                                   # panel top edge
        panel.appendSubstrate(box(minx - s - side, y0, minx - s, maxy))           # left rail
        panel.appendSubstrate(box(maxx + s, y0, maxx + s + side, maxy))           # right rail
        panel.appendSubstrate(box(minx - s - side, y0, maxx + s + side, miny - s))  # top rail
        return []
