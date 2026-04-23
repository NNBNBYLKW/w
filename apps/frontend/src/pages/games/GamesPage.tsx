import { GamesFeature } from "../../features/games/GamesFeature";


export function GamesPage() {
  return (
    <section className="page-card">
      <header className="page-header">
        <span className="page-header__eyebrow">Library subset surface</span>
        <h3>Games</h3>
        <p>
          Browse recognized game-entry files in a focused subset surface. Selection continues into shared details and
          the existing open actions.
        </p>
      </header>
      <GamesFeature />
    </section>
  );
}
