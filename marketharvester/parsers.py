import re
from html.parser import HTMLParser
from typing import List, Dict, Any, Optional


class SimpleDOMNode:
    def __init__(self, tag: str, attrs: Dict[str, str], parent: Optional["SimpleDOMNode"] = None):
        self.tag = tag
        self.attrs = attrs
        self.parent = parent
        self.children: List["SimpleDOMNode"] = []
        self.text_parts: List[str] = []

    @property
    def text(self) -> str:
        all_text = []
        def _collect(node: "SimpleDOMNode"):
            all_text.extend(node.text_parts)
            for child in node.children:
                _collect(child)
        _collect(self)
        return " ".join("".join(all_text).split())

    def get_attr(self, name: str) -> Optional[str]:
        return self.attrs.get(name)

    def find_all(self, tag: Optional[str] = None, class_name: Optional[str] = None) -> List["SimpleDOMNode"]:
        matches = []
        def _search(node: "SimpleDOMNode"):
            is_tag = tag is None or node.tag.lower() == tag.lower()
            is_class = True
            if class_name:
                node_classes = node.attrs.get("class", "").split()
                is_class = class_name in node_classes
            if is_tag and is_class and node is not self:
                matches.append(node)
            for child in node.children:
                _search(child)
        _search(self)
        return matches

    def find(self, tag: Optional[str] = None, class_name: Optional[str] = None) -> Optional["SimpleDOMNode"]:
        res = self.find_all(tag=tag, class_name=class_name)
        return res[0] if res else None


class MinimalHTMLTreeParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root = SimpleDOMNode("root", {})
        self.current = self.root

    def handle_starttag(self, tag: str, attrs: list):
        attr_dict = {k: v for k, v in attrs if v is not None}
        node = SimpleDOMNode(tag, attr_dict, parent=self.current)
        self.current.children.append(node)
        self.current = node

    def handle_endtag(self, tag: str):
        if self.current.parent is not None:
            self.current = self.current.parent

    def handle_data(self, data: str):
        if data:
            self.current.text_parts.append(data)


def parse_html_to_tree(html_content: str) -> SimpleDOMNode:
    parser = MinimalHTMLTreeParser()
    parser.feed(html_content)
    return parser.root


def extract_directory_listings(html_content: str, source_url: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extracts raw dictionary records from business directory HTML markup.
    Finds cards with classes 'business-card', 'listing-item', or 'company-entry'.
    """
    root = parse_html_to_tree(html_content)
    raw_records = []

    # Identify listing cards
    cards = []
    for cls in ["business-card", "listing-item", "company-entry", "directory-card"]:
        cards.extend(root.find_all(class_name=cls))

    # Fallback: if no specific class matched, look for <article> or div with data-company
    if not cards:
        cards = root.find_all(tag="article")

    for card in cards:
        # 1. Company Name
        name_node = card.find(class_name="company-name") or card.find(class_name="title") or card.find(tag="h2") or card.find(tag="h3")
        name = name_node.text if name_node else ""

        # 2. Category
        cat_node = card.find(class_name="category") or card.find(class_name="industry")
        category = cat_node.text if cat_node else "Uncategorized"

        # 3. Rating & Reviews
        rating = None
        rating_node = card.find(class_name="rating")
        if rating_node:
            raw_rating = rating_node.get_attr("data-rating") or rating_node.text
            match = re.search(r"(\d+(?:\.\d+)?)", raw_rating)
            if match:
                try:
                    rating = float(match.group(1))
                except ValueError:
                    pass

        review_count = 0
        review_node = card.find(class_name="reviews") or card.find(class_name="review-count")
        if review_node:
            match = re.search(r"(\d+)", review_node.text.replace(",", ""))
            if match:
                review_count = int(match.group(1))

        # 4. Contact Info
        phone_node = card.find(class_name="phone")
        phone = phone_node.text if phone_node else None
        if not phone:
            tel_link = card.find(tag="a")
            if tel_link and (tel_link.get_attr("href") or "").startswith("tel:"):
                phone = tel_link.get_attr("href").replace("tel:", "")

        email_node = card.find(class_name="email")
        email = email_node.text if email_node else None
        if not email:
            mail_links = card.find_all(tag="a")
            for link in mail_links:
                href = link.get_attr("href") or ""
                if href.startswith("mailto:"):
                    email = href.replace("mailto:", "")
                    break

        website_node = card.find(class_name="website")
        website = None
        if website_node:
            website = website_node.get_attr("href") or website_node.text
        if not website:
            links = card.find_all(tag="a")
            for link in links:
                href = link.get_attr("href") or ""
                if href.startswith("http://") or href.startswith("https://"):
                    website = href
                    break

        # 5. Address Details
        street_node = card.find(class_name="street") or card.find(class_name="address")
        street = street_node.text if street_node else None

        city_node = card.find(class_name="city")
        city = city_node.text if city_node else ""

        state_node = card.find(class_name="state")
        state = state_node.text if state_node else None

        zip_node = card.find(class_name="postal-code") or card.find(class_name="zip")
        postal_code = zip_node.text if zip_node else None

        country_node = card.find(class_name="country")
        country = country_node.text if country_node else "US"

        record = {
            "name": name,
            "category": category,
            "rating": rating,
            "review_count": review_count,
            "contact": {
                "email": email,
                "phone": phone,
                "website": website,
            },
            "address": {
                "street": street,
                "city": city,
                "state": state,
                "postal_code": postal_code,
                "country": country,
            },
            "source_url": source_url,
        }
        raw_records.append(record)

    return raw_records
