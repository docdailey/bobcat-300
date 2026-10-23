/**
 * bobcat-rak-stack-adapter (rev B of the Bobcat -> RAK5146 board; rev A was the
 * breakout interposer, circuits/bobcat-rak-interposer)
 *
 * Intent: a Mini Card-sized stack adapter. Its fingers go into the Bobcat Miner
 * 300 (G285) concentrator socket; a RAK5146-115 (SX1303, SPI) socket sits on top
 * right behind the fingers, so the RAK card lies directly over the adapter and
 * the Bobcat's original card area. No breakout, no jumper field.
 *
 * Electrical (Bobcat pins proven on a G285 with a DSLogic, 2026-10-22):
 *   Bobcat SCK 3 -> RAK 45, MISO 5 -> 47, MOSI 6 -> 49, CS 7 -> 51
 *   3.3 V  2/24/39/41/52 tied;  GND all ground pins + socket tabs;  22 straight
 *   19, 23 NOT connected; DNP 0402 0R options for 19, 23 (RAK GPS PPS out,
 *   GPS reset in) and 30-33 (RAK GPS I2C / UART) so they can be enabled later.
 *   Every other pin is left unconnected on both sides.
 *
 * Mechanics (PCI Express Mini Card Electromechanical Spec Rev 1.2):
 *   card 30.00 wide, 1.0 mm; contacts 0.60 x 2.55 / 0.80 pitch, odd on top
 *   (verified on a real card), key slot 1.50 x 4.00 at -3.85, corner notches;
 *   top-side component keep-out 3.20 from the edge (4.20 at the key, fig 2-7);
 *   Bobcat hold-down holes dia 2.6 at 48.05, 24.20 apart (fig 2-3).
 *   RAK socket: SOFNG PCIE-52P52H (LCSC C444927), card plane at 3.25 mm (card
 *   underside 2.75 mm). Everything of J1 (odd-row pads, solder tabs) reaches
 *   5.1 mm in front of its card-edge line S, so S = 9.3 puts all of it 4.2 mm
 *   from the finger edge: the stricter (key-area) value of the fig 2-7 top-side
 *   keep-out, applied across the whole width, so the Bobcat socket's housing lip
 *   is cleared anywhere along the edge. The RAK card then spans 9.3..60.3 mm, its
 *   hold-down holes sit at S + 48.05 = 57.35 mm (9.3 past the Bobcat holes), and
 *   the 5.8 mm keep-out square round them sets the 60.3 mm length. The socket's
 *   solder tabs reach x = +-15.3 mm (every Mini Card host socket is wider than
 *   the card), so the outline has 0.65 mm ears there.
 *
 * Fab profile: jlcpcb-2layer-cardedge (1.0 mm, ENIG, gold fingers, 30 deg bevel,
 * named card_edge override for the CE1/CE2 finger pads only).
 */
import { PCIE_52P52H } from "../../imports/PCIE_52P52H"

const SOCKET = (PCIE_52P52H({} as any) as any).props

// --- geometry (design frame: x across the card, y from the finger edge) -----
const S = 9.3 // RAK socket card-edge line: J1's front (S - 5.1) at 4.2 mm, fig 2-7 key-area keep-out
const L = 60.3 // S + 48.05 + half the 5.8 mm hold-down keep-out, rounded up
const EAR = 15.65 // half-width at the solder tabs: tab copper reaches +-15.3, plus the 0.3 mm edge rule
const TAB0 = +(S - 5.6).toFixed(2), TAB1 = +(S - 1.4).toFixed(2) // ears: tab copper S-5.1..S-1.9, +0.5
const Y0 = -L / 2
const Y = (y: number) => +(y + Y0).toFixed(4)
const CONTACT = 2.55

const fingerX = (n: number) =>
  +(n <= 16 ? -11.8 + 0.4 * (n - 1) : -2.2 + 0.4 * (n - 17)).toFixed(3)

const GND = [4, 9, 15, 18, 21, 26, 27, 29, 34, 35, 37, 40, 43, 50]
const PWR = [2, 24, 39, 41, 52]
const SPI: Record<number, number> = { 3: 45, 5: 47, 6: 49, 7: 51 }
const OPTIONS = [19, 23, 30, 31, 32, 33] // DNP 0R, Bobcat n <-> RAK n

const fingerNet = (n: number): string | undefined =>
  GND.includes(n) ? "net.GND"
    : PWR.includes(n) ? "net.V3V3"
      : n === 22 ? "net.RST22"
        : SPI[n] ? `net.SPI_${n}_${SPI[n]}`
          : OPTIONS.includes(n) ? `net.B${n}`
            : undefined
const socketNet = (n: number): string | undefined => {
  const spi = Object.entries(SPI).find(([, r]) => r === n)
  return GND.includes(n) ? "net.GND"
    : PWR.includes(n) ? "net.V3V3"
      : n === 22 ? "net.RST22"
        : spi ? `net.SPI_${spi[0]}_${n}`
          : OPTIONS.includes(n) ? `net.R${n}`
            : undefined
}

// --- outline ------------------------------------------------------------------
const slot = (() => {
  const cx = -3.85, r = 0.75, depth = 4.0
  const arc = Array.from({ length: 9 }, (_, i) => {
    const a = Math.PI - (Math.PI * i) / 8
    return { x: +(cx + r * Math.cos(a)).toFixed(4), y: +(depth - r + r * Math.sin(a)).toFixed(4) }
  })
  return [{ x: cx - r, y: 0 }, ...arc, { x: cx + r, y: 0 }]
})()
const OUTLINE = [
  { x: -12.85, y: 0 }, ...slot, { x: 12.85, y: 0 }, { x: 12.85, y: 3.2 },
  { x: 15, y: 3.2 }, { x: 15, y: TAB0 }, { x: EAR, y: TAB0 }, { x: EAR, y: TAB1 }, { x: 15, y: TAB1 },
  { x: 15, y: L }, { x: -15, y: L },
  { x: -15, y: TAB1 }, { x: -EAR, y: TAB1 }, { x: -EAR, y: TAB0 }, { x: -15, y: TAB0 },
  { x: -15, y: 3.2 }, { x: -12.85, y: 3.2 },
].map((p) => ({ x: p.x, y: Y(p.y) }))

// --- the card edge: two contact groups either side of the key -----------------
const pins = (a: number, b: number) => Array.from({ length: b - a + 1 }, (_, i) => a + i)
const CardEdge = ({ first, last, ...props }: any) => (
  <connector
    {...props}
    allowOffBoard
    pinLabels={Object.fromEntries(pins(first, last).map((n) => [`pin${n}`, [`pin${n}`]]))}
    pinAttributes={Object.fromEntries(pins(first, last).flatMap((n) =>
      fingerNet(n) === "net.V3V3" ? [[`pin${n}`, { providesPower: true, providesVoltage: 3.3 }]]
        : fingerNet(n) === "net.GND" ? [[`pin${n}`, { providesGround: true }]] : []))}
    manufacturerPartNumber="PCIe Mini Card edge (PCI-SIG Mini CEM 1.2)"
    connections={Object.fromEntries(pins(first, last).flatMap((n) =>
      fingerNet(n) ? [[`pin${n}`, fingerNet(n)]] : []))}
    footprint={
      <footprint insertionDirection="from_y_neg">
        {pins(first, last).map((n) => (
          <smtpad key={n} portHints={[`pin${n}`]} pcbX={`${fingerX(n)}mm`} pcbY={`${CONTACT / 2}mm`}
            width="0.6mm" height={`${CONTACT}mm`} shape="rect" layer={n % 2 ? "top" : "bottom"} />
        ))}
        <courtyardoutline outline={[
          { x: fingerX(first) - 0.5, y: 0 }, { x: fingerX(last) + 0.5, y: 0 },
          { x: fingerX(last) + 0.5, y: CONTACT + 0.25 }, { x: fingerX(first) - 0.5, y: CONTACT + 0.25 },
        ]} />
      </footprint>
    }
  />
)

// DNP 0R options, in a row behind the socket's even-pin row (y 15.1), 2.2 mm
// apart so each has room for its own via; socket side (pin 2) toward the socket
const OPTION_X = [-4.0, -1.8, 0.4, 2.6, 4.8, 7.0]
const OPTION_Y = S + 8.5

export default ({
  autorouter = "auto-local",
  routingDisabled = false,
  fab = {},
}: {
  autorouter?: string
  routingDisabled?: boolean
  fab?: Record<string, unknown>
} = {}) => (
  <board {...(fab as any)} outline={OUTLINE} layers={2}
    autorouter={autorouter as any} routingDisabled={routingDisabled}>
    <CardEdge name="CE1" first={1} last={16} pcbX={0} pcbY={Y(0)} />
    <CardEdge name="CE2" first={17} last={52} pcbX={0} pcbY={Y(0)} />

    <connector
      name="J1"
      footprint={SOCKET.footprint}
      cadModel={SOCKET.cadModel}
      supplierPartNumbers={SOCKET.supplierPartNumbers}
      manufacturerPartNumber={SOCKET.manufacturerPartNumber}
      pinLabels={SOCKET.pinLabels}
      pcbX={0}
      pcbY={Y(S)}
      pcbRotation={180}
      connections={Object.fromEntries([
        ...pins(1, 52).flatMap((n) => (socketNet(n) ? [[`pin${n}`, socketNet(n)]] : [])),
        ["pin53", "net.GND"],
        ["pin54", "net.GND"],
      ])}
    />

    {OPTIONS.map((n, i) => (
      <resistor key={n} name={`R${n}`} resistance="0" footprint="0402"
        pcbX={OPTION_X[i]} pcbY={Y(OPTION_Y)} pcbRotation={270}
        connections={{ pin1: `net.B${n}`, pin2: `net.R${n}` }} />
    ))}

    {/* Bobcat hold-down (card holes, fig 2-3) and RAK hold-down at S + 48.05 */}
    <hole diameter="2.6mm" pcbX={-12.1} pcbY={Y(48.05)} />
    <hole diameter="2.6mm" pcbX={12.1} pcbY={Y(48.05)} />
    <hole diameter="2.4mm" pcbX={-12.1} pcbY={Y(S + 48.05)} />
    <hole diameter="2.4mm" pcbX={12.1} pcbY={Y(S + 48.05)} />

    <silkscreentext text="BOBCAT G285 → RAK5146" pcbX={0} pcbY={Y(33)} fontSize="1.2mm" />
    <silkscreentext text="STACK ADAPTER  rev B" pcbX={0} pcbY={Y(31)} fontSize="1.2mm" />
    <silkscreentext text="SPI 3>45 5>47 6>49 7>51" pcbX={0} pcbY={Y(28.5)} fontSize="0.9mm" />
    <silkscreentext text="19 23 NC; R19 R23 R30-33 DNP 0R" pcbX={0} pcbY={Y(27)} fontSize="0.9mm" />
    <silkscreentext text="1.0mm ENIG 30deg BEVEL" pcbX={0} pcbY={Y(37)} fontSize="0.9mm" />

    <schematicsheet />
  </board>
)
