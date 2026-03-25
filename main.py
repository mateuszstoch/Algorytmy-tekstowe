import json
import re
from dataclasses import dataclass
from typing import List, Dict, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class Offer:
    id: int
    title: str
    company: str
    text: str
    required_skills: List[str]
    nice_to_have: List[str]


def load_offers(path: str) -> List[Offer]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    return [
        Offer(
            id=item["id"],
            title=item["title"],
            company=item["company"],
            text=item["text"],
            required_skills=item["required_skills"],
            nice_to_have=item["nice_to_have"],
        )
        for item in raw
    ]


def load_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def normalize_text(text: str) -> str:
    text = text.lower()
    text = text.replace("c++", "cpp")
    text = text.replace("c#", "csharp")
    text = re.sub(r"[^a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ0-9\s+#.]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_present_skills(text: str, skills_dictionary: List[str]) -> List[str]:
    text_norm = normalize_text(text)
    found = []

    for skill in skills_dictionary:
        skill_norm = normalize_text(skill)
        pattern = r"\b" + re.escape(skill_norm) + r"\b"
        if re.search(pattern, text_norm):
            found.append(skill)

    return sorted(set(found))


def compute_text_similarity(cv_text: str, offer_text: str) -> float:
    vectorizer = TfidfVectorizer(ngram_range=(1, 2))
    matrix = vectorizer.fit_transform([cv_text, offer_text])
    sim = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
    return float(sim)


def compute_skill_match(cv_skills: List[str], required_skills: List[str]) -> Tuple[float, List[str], List[str]]:
    cv_set = set(map(str.lower, cv_skills))
    req_set = set(map(str.lower, required_skills))

    matched = sorted(req_set.intersection(cv_set))
    missing = sorted(req_set - cv_set)

    coverage = len(matched) / len(req_set) if req_set else 0.0
    return coverage, matched, missing


def compute_nice_to_have_match(cv_skills: List[str], nice_to_have: List[str]) -> Tuple[float, List[str]]:
    cv_set = set(map(str.lower, cv_skills))
    nice_set = set(map(str.lower, nice_to_have))

    matched = sorted(nice_set.intersection(cv_set))
    coverage = len(matched) / len(nice_set) if nice_set else 0.0
    return coverage, matched


def compare_cv_to_offer(cv_text: str, offer: Offer, global_skills_dict: List[str]) -> Dict:
    cv_skills = extract_present_skills(cv_text, global_skills_dict)
    skill_coverage, matched_required, missing_required = compute_skill_match(cv_skills, offer.required_skills)
    nice_coverage, matched_nice = compute_nice_to_have_match(cv_skills, offer.nice_to_have)
    text_similarity = compute_text_similarity(normalize_text(cv_text), normalize_text(offer.text))

    final_score = (
        0.60 * skill_coverage +
        0.15 * nice_coverage +
        0.25 * text_similarity
    ) * 100

    extra_skills = sorted(set(map(str.lower, cv_skills)) - set(map(str.lower, offer.required_skills)) - set(map(str.lower, offer.nice_to_have)))

    return {
        "offer_id": offer.id,
        "title": offer.title,
        "company": offer.company,
        "score": round(final_score, 2),
        "text_similarity": round(text_similarity * 100, 2),
        "required_skill_coverage": round(skill_coverage * 100, 2),
        "nice_to_have_coverage": round(nice_coverage * 100, 2),
        "matched_required": matched_required,
        "missing_required": missing_required,
        "matched_nice": matched_nice,
        "extra_skills": extra_skills,
        "cv_skills": cv_skills,
    }


def build_global_skills_dictionary(offers: List[Offer]) -> List[str]:
    skills = set()
    for offer in offers:
        for s in offer.required_skills:
            skills.add(s.lower())
        for s in offer.nice_to_have:
            skills.add(s.lower())

    skills.update([
        "python", "java", "sql", "git", "linux", "docker", "django", "flask",
        "excel", "power bi", "pandas", "numpy", "statystyka", "analiza danych",
        "windows", "active directory", "helpdesk", "troubleshooting", "sieci",
        "oop", "spring", "hibernate", "rest api", "postgresql", "angielski",
        "testy jednostkowe", "jupyter"
    ])

    return sorted(skills)


def recommend_better_offers(cv_text: str, offers: List[Offer], skills_dict: List[str], threshold: float = 50.0) -> List[Dict]:
    results = [compare_cv_to_offer(cv_text, offer, skills_dict) for offer in offers]
    filtered = [r for r in results if r["score"] >= threshold]
    filtered.sort(key=lambda x: x["score"], reverse=True)
    return filtered


def print_result(result: Dict) -> None:
    print("\n" + "=" * 60)
    print(f"Oferta: {result['title']} | {result['company']}")
    print(f"Dopasowanie: {result['score']}%")
    print(f"Pokrycie wymaganych umiejętności: {result['required_skill_coverage']}%")
    print(f"Pokrycie mile widzianych: {result['nice_to_have_coverage']}%")
    print(f"Podobieństwo tekstowe TF-IDF: {result['text_similarity']}%")

    print("\nZgodności (wymagane):")
    print(", ".join(result["matched_required"]) if result["matched_required"] else "brak")

    print("\nBraki:")
    print(", ".join(result["missing_required"]) if result["missing_required"] else "brak")

    print("\nMile widziane znalezione w CV:")
    print(", ".join(result["matched_nice"]) if result["matched_nice"] else "brak")

    print("\nDodatkowe umiejętności z CV:")
    print(", ".join(result["extra_skills"]) if result["extra_skills"] else "brak")
    print("=" * 60)


def main():
    offers = load_offers("offers.json")
    cv_text = load_text("sample_cv.txt")
    skills_dict = build_global_skills_dictionary(offers)

    all_results = [compare_cv_to_offer(cv_text, offer, skills_dict) for offer in offers]
    all_results.sort(key=lambda x: x["score"], reverse=True)

    best = all_results[0]
    print_result(best)

    if best["score"] < 50:
        print("\nNajlepsza oferta ma mniej niż 50%. Szukam lepiej dopasowanych ofert...\n")
        recommendations = recommend_better_offers(cv_text, offers, skills_dict, threshold=50.0)

        if recommendations:
            print("Lepsze oferty:")
            for idx, rec in enumerate(recommendations[:5], start=1):
                print(f"{idx}. {rec['title']} | {rec['company']} -> {rec['score']}%")
        else:
            print("Nie znaleziono ofert z dopasowaniem >= 50%.")
    else:
        print("\nTop 3 najlepiej dopasowane oferty:")
        for idx, rec in enumerate(all_results[:3], start=1):
            print(f"{idx}. {rec['title']} | {rec['company']} -> {rec['score']}%")


if __name__ == "__main__":
    main()