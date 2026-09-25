from __future__ import annotations

import unittest
from datetime import UTC, datetime

from public_ai_challenge.phase1_scout_pipeline.contracts import (
    Availability,
    BuildInfo,
    CoverageSummary,
    Handling,
    HandlingType,
    IndexRelation,
    InformationCoverage,
    InteractionType,
    Municipality,
    MunicipalityDiscovery,
    MunicipalityService,
    ScoutStrategy,
    StrategyMode,
)


class ContractTests(unittest.TestCase):
    def test_discovery_round_trip(self):
        value = MunicipalityDiscovery(
            municipality=Municipality(
                name="Binn",
                canton="VS",
                official_url="https://www.binn.ch/",
            ),
            build=BuildInfo(
                run_id="binn-test",
                scouted_at=datetime.now(UTC),
                service_index_version="mvp-1",
            ),
            strategy=ScoutStrategy(
                mode=StrategyMode.BROAD_SMALL_SITE,
                reason="small",
                roots=["https://www.binn.ch/"],
                max_pages=20,
                max_depth=2,
            ),
            services=[
                MunicipalityService(
                    service_id="waste_collection",
                    local_name="Abfall",
                    index_relation=IndexRelation.INDEXED,
                    availability=Availability.SUPPORTED,
                    handling=Handling(
                        type=HandlingType.STATIC_PAGE,
                        interaction=InteractionType.INFORMATION,
                        summary="Municipal information page.",
                    ),
                    information=InformationCoverage(available=True),
                    confidence=0.9,
                )
            ],
            coverage=CoverageSummary(
                indexed_services_checked=5,
                supported=1,
                not_observed=4,
            ),
        )
        loaded = MunicipalityDiscovery.model_validate_json(
            value.model_dump_json()
        )
        self.assertEqual(loaded.schema, "municipality-discovery/v1")
        self.assertEqual(loaded.services[0].availability, Availability.SUPPORTED)

    def test_not_observed_is_distinct_from_unavailable(self):
        self.assertNotEqual(
            Availability.NOT_OBSERVED,
            Availability.UNAVAILABLE,
        )


if __name__ == "__main__":
    unittest.main()
