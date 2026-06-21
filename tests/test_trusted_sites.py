"""Test domini trusted e query restrittive."""

from drug_image_fetcher.search.trusted_sites import (
    build_restricted_search_query,
    build_site_restriction_clause,
    is_trusted_url,
    resolve_manufacturer_search_url,
)


def test_is_trusted_url_aifa() -> None:
    assert is_trusted_url(
        "https://farmaci.agenziafarmaco.gov.it/bancadatifarmaci/farmaco?aic=123"
    )


def test_is_trusted_url_rejects_unknown() -> None:
    assert not is_trusted_url("https://random-blog.example.com/farmaco")


def test_build_site_restriction_clause() -> None:
    clause = build_site_restriction_clause(["farmaciaigea.com", "farmae.it"])
    assert "site:farmaciaigea.com" in clause
    assert "OR" in clause


def test_build_restricted_search_query() -> None:
    q = build_restricted_search_query(
        "027606012 Tachipirina",
        ["farmaciaigea.com"],
    )
    assert "027606012 Tachipirina" in q
    assert "site:farmaciaigea.com" in q


def test_resolve_manufacturer_search_url_angelini() -> None:
    url = resolve_manufacturer_search_url("Angelini Pharma S.p.A.", "Tachipirina 500")
    assert url is not None
    assert "angelini.it" in url
