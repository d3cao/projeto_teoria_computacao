from statistics import correlation
import unittest
from itertools import product

from triagem import configurar, gerar, discretizar, alfabeto, treinar, percurso


class TriagemTest(unittest.TestCase):
    def setUp(self):
        self.cfg = configurar()

    def test_geracao(self):
        treino, teste = gerar(self.cfg, 42, 2000, 500)
        self.assertEqual((treino, teste), gerar(self.cfg, 42, 2000, 500))
        self.assertEqual((len(treino), len(teste)), (2000, 500))
        self.assertFalse({a["id"] for a in treino} & {a["id"] for a in teste})
        self.assertEqual(teste, gerar(self.cfg, 42, 3, 500)[1])
        self.assertTrue(any(a["fps"] > 6 and not a["viavel"] for a in treino))
        self.assertTrue(any(a["fps"] > 6 and a["uv"] < 0.4 for a in treino))
        self.assertTrue(all(a["viavel"] == (a["dna"] >= self.cfg["corte_dna"])
                            for a in treino + teste))
        fps = [a["fps"] for a in treino]
        self.assertGreater(correlation([a["fenois"] for a in treino], fps), 0)
        self.assertLess(correlation([a["dpph"] for a in treino], fps), 0)

    def test_fronteiras(self):
        a = dict(ccd="MODERADO", fenois=150, dpph=500, fps=6, uv=0.7)
        self.assertEqual(discretizar(a, self.cfg, 5),
                         ("ccd:2", "fenois:2", "dpph:4", "fps:2", "uv:3"))
        self.assertEqual(discretizar(a, self.cfg, 3),
                         ("ccd:2", "fenois:2", "dpph:3", "fps:1", "uv:3"))
        a.update(fenois=50, dpph=50, fps=60)
        self.assertEqual(discretizar(a, self.cfg, 5)[1:4],
                         ("fenois:2", "dpph:2", "fps:5"))

    def test_moore(self):
        grupos = alfabeto(self.cfg, 3)
        a, b, c = list(product(*grupos[:4]))[:3]
        uv1, uv2, uv3 = grupos[4]
        dados = [(a + (uv1,), 0)] * 3 + [(b + (uv1,), 0)] * 3
        dados += [(b + (uv2,), 1), (b + (uv2,), 0), (c + (uv1,), 0)]
        arvore = treinar(dados, grupos, 3, fundir=False)
        maquina = treinar(dados, grupos, 3)
        self.assertLess(len(maquina["estados"]), len(arvore["estados"]))

        def saidas(modelo, rastro):
            return [modelo["saidas"][q] for q in percurso(modelo, rastro)]

        self.assertEqual(saidas(maquina, a + (uv1,)), ["AVANCAR"] * 4 + ["DESCARTAR"] * 2)
        self.assertEqual(saidas(maquina, b + (uv1,))[-2:], ["AVANCAR", "DESCARTAR"])
        self.assertEqual(saidas(maquina, b + (uv2,)), ["AVANCAR"] * 6)
        self.assertEqual(saidas(maquina, b + (uv3,)), ["AVANCAR"] * 6)
        self.assertEqual(saidas(maquina, c + (uv1,)), ["AVANCAR"] * 6)
        for rastro in product(*grupos):
            self.assertEqual(saidas(arvore, rastro), saidas(maquina, rastro))
        for estado in maquina["estados"]:
            self.assertEqual(set(maquina["transicoes"][estado]), set(maquina["alfabeto"]))


if __name__ == "__main__":
    unittest.main()
