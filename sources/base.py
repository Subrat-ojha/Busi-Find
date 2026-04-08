from dataclasses import dataclass, field


@dataclass
class Business:
    """Represents a business found from any source."""
    name: str
    address: str = ""
    phone: str = ""
    website: str = ""
    rating: float = 0.0
    review_count: int = 0
    category: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    source: str = ""
    has_website: bool = False

    def to_dict(self):
        return {
            "name": self.name,
            "address": self.address,
            "phone": self.phone,
            "website": self.website,
            "rating": self.rating,
            "review_count": self.review_count,
            "category": self.category,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "source": self.source,
            "has_website": self.has_website,
        }
