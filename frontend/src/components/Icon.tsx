import arrowRBlanc from "../assets/icons/arrow-r-blanc.svg";
import arrowRLegende from "../assets/icons/arrow-r-legende.svg";
import checkCase from "../assets/icons/check-case.svg";
import checkEtape from "../assets/icons/check-etape.svg";
import checkLegende from "../assets/icons/check-legende.svg";
import chevDArbo from "../assets/icons/chev-d-arbo.svg";
import chevDChamp from "../assets/icons/chev-d-champ.svg";
import chevDNav from "../assets/icons/chev-d-nav.svg";
import chevLBarre from "../assets/icons/chev-l-barre.svg";
import chevLBouton from "../assets/icons/chev-l-bouton.svg";
import chevRAnnexe from "../assets/icons/chev-r-annexe.svg";
import chevUNav from "../assets/icons/chev-u-nav.svg";
import clockCarte from "../assets/icons/clock-carte.svg";
import clockCase from "../assets/icons/clock-case.svg";
import clockLegende from "../assets/icons/clock-legende.svg";
import comment from "../assets/icons/comment.svg";
import copy from "../assets/icons/copy.svg";
import file from "../assets/icons/file.svg";
import folderArbo from "../assets/icons/folder-arbo.svg";
import folderBlanc from "../assets/icons/folder-blanc.svg";
import folderChamp from "../assets/icons/folder-champ.svg";
import folderPlus from "../assets/icons/folder-plus.svg";
import insert from "../assets/icons/insert.svg";
import list from "../assets/icons/list.svg";
import more from "../assets/icons/more.svg";
import pencil from "../assets/icons/pencil.svg";
import plus from "../assets/icons/plus.svg";
import save from "../assets/icons/save.svg";
import search from "../assets/icons/search.svg";
import sparkleArbo from "../assets/icons/sparkle-arbo.svg";
import sparkleBascule from "../assets/icons/sparkle-bascule.svg";
import sparkleEntete from "../assets/icons/sparkle-entete.svg";
import sparkleNote from "../assets/icons/sparkle-note.svg";
import sparklePetit from "../assets/icons/sparkle-petit.svg";
import sparkleRail from "../assets/icons/sparkle-rail.svg";
import undo from "../assets/icons/undo.svg";
import xDialogue from "../assets/icons/x-dialogue.svg";
import xPanneau from "../assets/icons/x-panneau.svg";

/** Encart du tracé dans la boîte de l'icône, en % : [haut, droite, bas, gauche] (comme dans Figma). */
type Encart = [number, number, number, number];

const CHEV_L: Encart = [25, 37.5, 25, 37.5];
const CHEV_D: Encart = [37.5, 25, 37.5, 25];
const CHECK: Encart = [31.25, 20.83, 29.17, 20.83];
const SPARKLE: Encart = [12.5, 12.5, 20.83, 20.83];
const FOLDER: Encart = [20.83, 12.5, 20.83, 12.5];
const ARROW_R: Encart = [25, 20.83, 25, 20.83];
const CLOCK: Encart = [16.67, 16.67, 16.67, 16.67];

/**
 * Chaque SVG exporté de Figma a sa propre taille intrinsèque (tracé + épaisseur du trait).
 * On le centre sur le groupe défini par l'encart, sans le redimensionner.
 */
const ICONES = {
  "arrow-r-blanc": { src: arrowRBlanc, boite: 16, encart: ARROW_R, l: 11.1333, h: 9.8 },
  "arrow-r-legende": { src: arrowRLegende, boite: 12, encart: ARROW_R, l: 8.8, h: 7.8 },
  "check-case": { src: checkCase, boite: 14, encart: CHECK, l: 10.7667, h: 8.14167 },
  "check-etape": { src: checkEtape, boite: 14, encart: CHECK, l: 10.5667, h: 7.94167 },
  "check-legende": { src: checkLegende, boite: 10, encart: CHECK, l: 8.83333, h: 6.95833 },
  "chev-d-arbo": { src: chevDArbo, boite: 14, encart: CHEV_D, l: 8.8, h: 5.3 },
  "chev-d-champ": { src: chevDChamp, boite: 16, encart: CHEV_D, l: 9.8, h: 5.8 },
  "chev-d-outils": { src: chevDArbo, boite: 14, encart: CHEV_D, l: 8.8, h: 5.3 },
  "chev-d-nav": { src: chevDNav, boite: 16, encart: CHEV_D, l: 9.8, h: 5.8 },
  "chev-u-nav": { src: chevUNav, boite: 16, encart: CHEV_D, l: 9.8, h: 5.8 },
  "chev-l-barre": { src: chevLBarre, boite: 16, encart: CHEV_L, l: 5.8, h: 9.8 },
  "chev-l-bouton": { src: chevLBouton, boite: 16, encart: CHEV_L, l: 5.8, h: 9.8 },
  "chev-r-annexe": { src: chevRAnnexe, boite: 14, encart: CHEV_L, l: 5.3, h: 8.8 },
  "clock-carte": { src: clockCarte, boite: 14, encart: [12.5, 12.5, 12.5, 12.5] as Encart, l: 12.3, h: 12.3 },
  "clock-case": { src: clockCase, boite: 14, encart: CLOCK, l: 11.5333, h: 11.5333 },
  "clock-legende": { src: clockLegende, boite: 10, encart: CLOCK, l: 9.26667, h: 9.26667 },
  comment: { src: comment, boite: 16, encart: [23.17, 12.5, 16.37, 16.67] as Encart, l: 13.1336, h: 11.4741 },
  copy: { src: copy, boite: 14, encart: CLOCK, l: 11.1333, h: 11.1333 },
  file: { src: file, boite: 16, encart: [12.5, 20.83, 12.5, 20.83] as Encart, l: 11.1333, h: 13.8 },
  "folder-arbo": { src: folderArbo, boite: 15, encart: FOLDER, l: 13.05, h: 10.55 },
  "folder-blanc": { src: folderBlanc, boite: 16, encart: FOLDER, l: 13.8, h: 11.1333 },
  "folder-champ": { src: folderChamp, boite: 16, encart: FOLDER, l: 13.8, h: 11.1333 },
  "folder-plus": { src: folderPlus, boite: 24, encart: FOLDER, l: 19.8, h: 15.8 },
  insert: { src: insert, boite: 14, encart: [20.83, 20.83, 20.83, 20.83] as Encart, l: 9.96667, h: 9.96667 },
  list: { src: list, boite: 16, encart: [25, 16.67, 25, 16.67] as Encart, l: 12.4667, h: 9.8 },
  more: { src: more, boite: 16, encart: [45.83, 8.33, 45.83, 8.33] as Encart, l: 13.8, h: 3.3 },
  pencil: { src: pencil, boite: 14, encart: [20.83, 20.83, 16.67, 16.67] as Encart, l: 10.55, h: 10.55 },
  plus: { src: plus, boite: 15, encart: [20.83, 20.83, 20.83, 20.83] as Encart, l: 10.55, h: 10.55 },
  save: { src: save, boite: 16, encart: [12.5, 20.83, 12.5, 20.83] as Encart, l: 11.1333, h: 13.8 },
  search: { src: search, boite: 16, encart: CLOCK, l: 12.4667, h: 12.4667 },
  "sparkle-arbo": { src: sparkleArbo, boite: 15, encart: SPARKLE, l: 11.8, h: 11.8 },
  "sparkle-bascule": { src: sparkleBascule, boite: 16, encart: SPARKLE, l: 12.4667, h: 12.4667 },
  "sparkle-entete": { src: sparkleEntete, boite: 17, encart: SPARKLE, l: 13.1333, h: 13.1333 },
  "sparkle-note": { src: sparkleNote, boite: 13, encart: SPARKLE, l: 10.4667, h: 10.4667 },
  "sparkle-petit": { src: sparklePetit, boite: 14, encart: SPARKLE, l: 11.1333, h: 11.1333 },
  "sparkle-rail": { src: sparkleRail, boite: 19, encart: SPARKLE, l: 14.4667, h: 14.4667 },
  undo: { src: undo, boite: 16, encart: [16.67, 16.67, 12.5, 16.67] as Encart, l: 12.4667, h: 13.1333 },
  "x-dialogue": { src: xDialogue, boite: 18, encart: [25, 25, 25, 25] as Encart, l: 10.8, h: 10.8 },
  "x-panneau": { src: xPanneau, boite: 16, encart: [25, 25, 25, 25] as Encart, l: 9.8, h: 9.8 },
};

export type NomIcone = keyof typeof ICONES;

export function Icon({ nom, className }: { nom: NomIcone; className?: string }) {
  const { src, boite, encart, l, h } = ICONES[nom];
  const [haut, droite, bas, gauche] = encart.map((p) => (p / 100) * boite);
  const groupeL = boite - gauche - droite;
  const groupeH = boite - haut - bas;
  const left = gauche - (l - groupeL) / 2;
  const top = haut - (h - groupeH) / 2;

  return (
    <span className={`icone ${className ?? ""}`} style={{ width: boite, height: boite }} aria-hidden="true">
      <img src={src} alt="" style={{ left, top }} />
    </span>
  );
}
