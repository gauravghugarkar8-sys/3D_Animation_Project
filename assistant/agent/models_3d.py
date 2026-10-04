"""
A small curated table mapping common knowledge topics to real, freely
embeddable Sketchfab 3D models (verified public "Download Free 3D model"
listings, embedded via Sketchfab's standard /models/<uid>/embed iframe
URL — see https://sketchfab.com/developers/oembed).

This is what lets "tell me about the heart" swap the centre panel to an
actual rotating, zoomable 3D model — the Django-side equivalent of the
anatomy-model viewer in the reference recording — instead of a flat
image. Anything not in this table still falls back to a Wikipedia image
(see agent/tools.py::wiki_lookup and agent/core_agent.py).

Extend this dict any time: pick a "Download Free 3D model" page on
sketchfab.com, copy the id from its URL
(sketchfab.com/3d-models/<slug>-<32-char-id>) and add an entry below.
"""

MODEL_3D_LIBRARY = {
    "heart": {
        "title": "Human Heart — External Anatomy",
        "sketchfab_uid": "a3f0ea2030214a6bbaa97e7357eebd58",
        "keywords": ["heart", "cardiac", "cardiovascular"],
    },
    "heart_coronary": {
        "title": "Human Heart — Coronary Arteries",
        "sketchfab_uid": "00b5f4ec0b984325b453f8df07cd0cb5",
        "keywords": ["coronary artery", "coronary arteries"],
    },
    "brain": {
        "title": "Human Brain Anatomy",
        "sketchfab_uid": "0aa0e33c5c854d1bab7bac9e1c7acaec",
        "keywords": ["brain", "cerebrum", "cerebellum", "brainstem"],
    },
    "skull": {
        "title": "Human Skull Anatomy",
        "sketchfab_uid": "baf6ac7b781a46218dca2b59dee58817",
        "keywords": ["skull", "cranium", "jaw", "mandible"],
    },
    "skeleton": {
        "title": "Human Skeleton",
        "sketchfab_uid": "071ecfa34d904c9b99b816b9509124b5",
        "keywords": ["skeleton", "bones", "bone structure", "osteology"],
    },
    "dna": {
        "title": "DNA — Double Helix",
        "sketchfab_uid": "60e95170b37549e3b45ee490b74bb112",
        "keywords": ["dna", "double helix", "genome", "genetics", "chromosome"],
    },
    "earth": {
        "title": "Planet Earth",
        "sketchfab_uid": "41fc80d85dfd480281f21b74b2de2faa",
        "keywords": ["earth", "planet earth", "the world"],
    },
    "solar_system": {
        "title": "The Solar System",
        "sketchfab_uid": "d3f058bbe20e4f70b2b52277ff8e109a",
        "keywords": ["solar system", "planets", "the sun", "orbit"],
    },
    "stomach": {
        "title": "Human Stomach Anatomy",
        "sketchfab_uid": "94c42e484d3d4e29b751e6224f49694e",
        "keywords": ["stomach", "gastric"],
    },
    "digestive_system": {
        "title": "Human Digestive System",
        "sketchfab_uid": "f078cef244ec481e93013982a5393ffe",
        "keywords": ["digestive system", "digestion", "intestine", "intestines"],
    },
    "lungs": {
        "title": "Human Lungs (with Heart)",
        "sketchfab_uid": "45f09e9f193640729294da60e9962bc8",
        "keywords": ["lungs", "lung", "respiratory system", "breathing"],
    },
}


def find_3d_model(topic):
    """
    Best-effort keyword match against the curated library.
    Returns {"title", "embed_url"} or None.
    """
    if not topic:
        return None
    topic_lower = topic.lower()

    best_entry = None
    best_score = 0
    for entry in MODEL_3D_LIBRARY.values():
        for kw in entry["keywords"]:
            if kw in topic_lower:
                score = len(kw)  # longer/more specific keyword wins
                if score > best_score:
                    best_score = score
                    best_entry = entry

    if not best_entry:
        return None

    return {
        "title": best_entry["title"],
        "embed_url": f"https://sketchfab.com/models/{best_entry['sketchfab_uid']}/embed"
                      f"?autostart=1&ui_theme=dark",
    }
