import unittest

import numpy as np

from egaliseur.filtres import EgaliseurLissage, passe_bas

FS = 44_100


def ton(frequence, duree=2.0):
    t = np.arange(int(duree * FS)) / FS
    return np.sin(2 * np.pi * frequence * t)


def gain_db(entree, sortie):
    milieu = slice(len(entree) // 4, 3 * len(entree) // 4)  # loin des bords (régime transitoire)
    return 20 * np.log10(np.std(sortie[milieu]) / np.std(entree[milieu]))


class FiltresTests(unittest.TestCase):
    def test_passe_bas_vaut_moins_3_db_a_la_coupure(self) -> None:
        x = ton(250)
        self.assertAlmostEqual(gain_db(x, passe_bas(x, 250, FS)), -3.0, delta=0.15)

    def test_passe_bas_laisse_passer_les_graves_et_coupe_les_aigus(self) -> None:
        self.assertGreater(gain_db(ton(50), passe_bas(ton(50), 250, FS)), -0.5)
        self.assertLess(gain_db(ton(5000), passe_bas(ton(5000), 250, FS)), -40)

    def test_les_trois_bandes_recomposent_exactement_le_signal(self) -> None:
        x = np.random.default_rng(1).uniform(-0.5, 0.5, size=(20_000, 2))
        egaliseur = EgaliseurLissage()
        bandes = egaliseur.split_bands(x, FS, 250, 4000)
        neutre = egaliseur.apply_gains(bandes, {"bass": 0, "mid": 0, "treble": 0})
        np.testing.assert_allclose(egaliseur.recombine_bands(neutre), x, atol=1e-12)

    def test_chaque_note_tombe_dans_sa_bande(self) -> None:
        egaliseur = EgaliseurLissage()
        for frequence, attendue in ((60, "bass"), (1000, "mid"), (15000, "treble")):
            bandes = egaliseur.split_bands(ton(frequence), FS, 250, 4000)
            energies = {nom: np.std(signal) for nom, signal in bandes.items()}
            self.assertEqual(max(energies, key=energies.get), attendue, frequence)


if __name__ == "__main__":
    unittest.main()
