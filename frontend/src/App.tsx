import { useState } from "react";
import { Accueil } from "./screens/Accueil";
import { Editeur } from "./screens/Editeur";
import { Pipeline } from "./screens/Pipeline";

type Ecran = "accueil" | "pipeline" | "editeur";

export function App() {
  const [ecran, setEcran] = useState<Ecran>("accueil");
  const accueil = () => setEcran("accueil");

  if (ecran === "pipeline") return <Pipeline onQuitter={accueil} onTerminer={() => setEcran("editeur")} />;
  if (ecran === "editeur") return <Editeur onQuitter={accueil} />;
  return <Accueil onDemarrer={() => setEcran("pipeline")} onOuvrir={() => setEcran("editeur")} />;
}
