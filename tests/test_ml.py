import json, numpy as np
from app.ml.model import GDLogisticRegression, bce, sigmoid
from app.ml.synthetic import make_split, featurize
from app.ml.train import ART, scores


def test_bce_finite_at_extremes():
    assert np.isfinite(bce(np.array([1.0, 0.0]), np.array([0.0, 1.0])))


def test_analytic_gradient_matches_numerical():
    r = np.random.default_rng(0); Z = r.normal(size=(40, 3)); y = (Z[:, 0] + .3 * r.normal(size=40) > 0).astype(float)
    w, b = r.normal(size=3), 0.1
    analytic = Z.T @ (sigmoid(Z @ w + b) - y) / len(y)
    num = []
    for j in range(3):
        e = np.zeros(3); e[j] = 1e-6
        num.append((bce(y, sigmoid(Z @ (w + e) + b)) - bce(y, sigmoid(Z @ (w - e) + b))) / 2e-6)
    assert np.allclose(analytic, num, atol=1e-6)


def test_training_reduces_loss_and_learns():
    sp = make_split(seed=3, n=300)
    Xtr, ytr, _, _ = featurize(sp["train"]); Xte, yte, _, _ = featurize(sp["test"])
    m = GDLogisticRegression(iters=300).fit(Xtr, ytr)
    assert m.loss[-1] < 0.5 * m.loss[0]
    assert scores(yte, (m.predict_proba(Xte) >= .5).astype(int))["f1"] > 0.7


def test_no_invoice_shared_between_train_and_test():
    sp = make_split(seed=5, n=200)
    ids = lambda part: set().union(*[p[4] for p in sp[part]])
    assert ids("train").isdisjoint(ids("test"))


def test_saved_metrics_match_recomputation():
    m = json.loads((ART / "metrics.json").read_text())
    model = GDLogisticRegression.from_dict(json.loads((ART / "model.json").read_text()))
    X, y, _, _ = featurize(make_split(m["seed"])["test"])
    got = scores(y, (model.predict_proba(X) >= m["threshold"]).astype(int))
    assert got == m["model"]
