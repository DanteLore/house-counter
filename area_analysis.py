from dataclasses import dataclass, field
from typing import Callable, Optional
from geo import polygon_area_m2


@dataclass
class PolygonAnalysis:
    geojson_coords: list
    uprn_count: Optional[int] = field(default=None)

    @property
    def area_m2(self) -> float:
        return polygon_area_m2(self.geojson_coords)

    @property
    def density_m2_per_address(self) -> Optional[float]:
        if self.uprn_count is None or self.uprn_count == 0:
            return None
        return self.area_m2 / self.uprn_count

    def fetch_count(self, fetcher: Callable[[list], int]) -> None:
        self.uprn_count = fetcher(self.geojson_coords)
