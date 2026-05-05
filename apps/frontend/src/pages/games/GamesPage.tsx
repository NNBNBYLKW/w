import { GamesFeature } from "../../features/games/GamesFeature";
import { t } from "../../shared/text";


export function GamesPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">{t("pages.games.eyebrow")}</span>
        <h3>{t("pages.games.title")}</h3>
        <p>{t("pages.games.description")}</p>
      </header>
      <GamesFeature />
    </section>
  );
}
