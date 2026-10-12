"""v7.0 — domain cards in the interface."""
from __future__ import annotations

import domains


def test_domain_cards(page, evidence):
    page.wait_for_selector("#domainList [data-domain]")
    cards = page.locator("#domainList [data-domain]").count()
    bio = page.inner_text('#domainList [data-domain="exploratory_biomedical"]')
    assert cards == len(domains.DOMAINS) and "conseil médical" in bio and "Exclu" in bio and "cas de référence" in bio
    evidence("Domaines scientifiques", "Ouvrir la section « Domaines »", "Périmètre, exclusions, cas de référence et statut dérivé pour chaque domaine",
             f"{cards} domaines ; {bio.splitlines()[0]}")
