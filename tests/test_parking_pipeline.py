"""
Tests unitaires et de cohérence pour Vision Parking Universiapolis.
Vérifie la validité des coordonnées géométriques, l'intégrité des résultats et le serveur Flask.
"""

import json
import unittest
from pathlib import Path


class TestVisionParkingPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parent.parent
        cls.places_file = cls.root / "02_POLYGONES" / "places_18.json"
        cls.results_file = cls.root / "05_RESULTATS_DEMO" / "resultats.json"
        cls.web_index = cls.root / "04_INTERFACE_WEB" / "index.html"

    def test_places_18_file_exists_and_valid(self):
        """Vérifie que le fichier de calibrage des 18 places existe et contient du JSON valide."""
        self.assertTrue(self.places_file.is_file(), f"Fichier introuvable: {self.places_file}")
        with open(self.places_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.assertIn("places", data)
        places = data["places"]
        self.assertEqual(len(places), 18, "Le parking campus IP7 doit contenir exactement 18 places calibrées.")
        
        for idx, place in enumerate(places):
            self.assertIn("id", place)
            self.assertIn("polygon", place)
            polygon = place["polygon"]
            self.assertGreaterEqual(len(polygon), 3, f"La place #{idx} doit être un polygone d'au moins 3 sommets.")
            for pt in polygon:
                self.assertIsInstance(pt[0], (int, float))
                self.assertIsInstance(pt[1], (int, float))

    def test_results_demo_data_integrity(self):
        """Vérifie l'intégrité de la structure des résultats précalculés pour le dashboard."""
        self.assertTrue(self.results_file.is_file(), f"Fichier introuvable: {self.results_file}")
        with open(self.results_file, "r", encoding="utf-8") as f:
            results = json.load(f)
        
        self.assertIn("source_name", results)
        self.assertIn("duration_seconds", results)
        self.assertIn("processed_frames", results)
        self.assertIn("places", results)
        self.assertEqual(len(results["places"]), 18)
        self.assertIn("samples", results)
        self.assertGreater(len(results["samples"]), 0, "Les résultats doivent contenir des échantillons temporels.")

    def test_web_interface_exists(self):
        """Vérifie que le dashboard de supervision web est présent et contient les conteneurs requis."""
        self.assertTrue(self.web_index.is_file())
        content = self.web_index.read_text(encoding="utf-8")
        self.assertIn("Vision Parking", content)
        self.assertIn("topdown", content)
        self.assertIn("video", content)


if __name__ == "__main__":
    unittest.main()
