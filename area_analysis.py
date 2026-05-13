from dataclasses import dataclass, field
from typing import Callable, Optional
from geo import polygon_area_m2


@dataclass
class PolygonAnalysis:
    geojson_coords: list
    uprn_count: Optional[int] = field(default=None)
    uprn_points: Optional[list] = field(default=None)  # list of {lat, lon}

    @property
    def area_m2(self) -> float:
        return polygon_area_m2(self.geojson_coords)

    @property
    def area_ha(self) -> float:
        return self.area_m2 / 10_000

    @property
    def density_m2_per_address(self) -> Optional[float]:
        if self.uprn_count is None or self.uprn_count == 0:
            return None
        return self.area_m2 / self.uprn_count

    @property
    def dwellings_per_hectare(self) -> Optional[float]:
        if self.uprn_count is None or self.uprn_count == 0:
            return None
        return self.uprn_count / self.area_ha

    def fetch_count(self, fetcher: Callable[[list], int]) -> None:
        self.uprn_count = fetcher(self.geojson_coords)

    def fetch_points(self, fetcher: Callable[[list], list]) -> None:
        self.uprn_points = fetcher(self.geojson_coords)
        self.uprn_count = len(self.uprn_points)
