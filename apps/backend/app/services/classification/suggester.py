class RuleBasedSuggester:
    def suggest(self, name: str, path: str) -> list[dict]:
        suggestions = []
        n = name.lower()
        p = path.lower()
        if any(kw in n for kw in ["movie", "film", "episode", "season"]):
            suggestions.append({"type": "movie", "placement": "media", "confidence": 0.6, "reason": "Filename contains media keywords"})
        if any(kw in n for kw in ["setup", "install", "portable", "crack"]):
            suggestions.append({"type": "software", "placement": "software", "confidence": 0.7, "reason": "Filename suggests software"})
        if any(kw in p for kw in ["games", "game", "steam", "epic"]):
            suggestions.append({"type": "game", "placement": "games", "confidence": 0.8, "reason": "File is in a game directory"})
        if any(kw in p for kw in ["books", "ebooks", "documents", "docs"]):
            suggestions.append({"type": "document", "placement": "books", "confidence": 0.7, "reason": "File is in a document directory"})
        return suggestions
