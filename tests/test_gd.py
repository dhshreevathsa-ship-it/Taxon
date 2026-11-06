import numpy as np, pytest
from fastapi.testclient import TestClient
from app.main import app
from app.ml import service
from app.ml.features import FEATURES, vectorize
from app.ml.model import GDLogisticRegression, bce, classification_metrics, gd_step, gradients, sigmoid, validate_params
from app.ml.synthetic import make_split

mk = lambda: TestClient(app)


def test_sigmoid_values_and_numerical_stability():
    with np.errstate(over="raise", invalid="raise", divide="raise"):  # underflow to 0 is harmless; overflow/NaN must never happen
        s = sigmoid(np.array([-1000.0, -30.0, 0.0, 30.0, 1000.0]))
    assert s[2] == 0.5 and s[0] == 0.0 and s[4] == 1.0 and np.all((s >= 0) & (s <= 1))
    z = np.linspace(-8, 8, 9); assert np.allclose(sigmoid(-z), 1 - sigmoid(z))


def test_bce_known_values_and_clipping():
    assert bce(np.array([1.0]), np.array([0.5])) == pytest.approx(np.log(2))
    assert bce(np.array([1.0, 0.0]), np.array([1.0, 0.0])) < 1e-9
    assert np.isfinite(bce(np.array([1.0]), np.array([0.0]))) and np.isfinite(bce(np.array([0.0]), np.array([1.0]))) and bce(np.array([1.0]), np.array([0.0])) > 20


@pytest.mark.parametrize("l2", [0.0, 0.05])
def test_analytic_gradients_match_finite_differences(l2):
    r = np.random.default_rng(1); Z = r.normal(size=(30, 4)); y = (r.random(30) > 0.5).astype(float); w, b = r.normal(size=4), 0.3
    J = lambda w, b: bce(y, sigmoid(Z @ w + b)) + 0.5 * l2 * float(w @ w)
    gw, gb, _ = gradients(Z, y, w, b, l2); h = 1e-6
    num_w = [(J(w + h * e, b) - J(w - h * e, b)) / (2 * h) for e in np.eye(4)]
    assert np.allclose(gw, num_w, atol=1e-7) and gb == pytest.approx((J(w, b + h) - J(w, b - h)) / (2 * h), abs=1e-7)


def test_update_rule_is_minus_alpha_times_gradient():
    w, b = gd_step(np.array([1.0, -2.0]), 0.5, np.array([0.2, -0.4]), 0.1, 0.5)
    assert np.allclose(w, [0.9, -1.8]) and b == pytest.approx(0.45)


def test_hand_worked_example_for_the_appendix():
    x, y = np.array([[1.0], [3.0]]), np.array([0.0, 1.0]); w, b = np.zeros(1), 0.0
    gw, gb, p = gradients(x, y, w, b)
    assert np.allclose(p, 0.5) and bce(y, p) == pytest.approx(np.log(2)) and gw[0] == pytest.approx(-0.5) and gb == pytest.approx(0.0)
    w1, b1 = gd_step(w, b, gw, gb, 1.0); p1 = sigmoid(x @ w1 + b1)
    assert w1[0] == pytest.approx(0.5) and b1 == pytest.approx(0.0) and np.allclose(p1, [0.622459, 0.817574], atol=1e-6) and bce(y, p1) == pytest.approx(0.587745, abs=1e-6)


def test_training_reduces_loss_on_separable_data():
    r = np.random.default_rng(0); X = np.r_[r.normal(-2, 1, (60, 1)), r.normal(2, 1, (60, 1))]; y = np.r_[np.zeros(60), np.ones(60)]
    m = GDLogisticRegression(lr=0.1, iters=300, l2=0.0).fit(X, y)
    assert m.loss[-1] < m.loss[0] and all(b <= a + 1e-12 for a, b in zip(m.loss, m.loss[1:])) and classification_metrics(y, m.predict_proba(X))["accuracy"] >= 0.95 and len(m.loss) == 301


def test_invalid_parameters_and_data_are_rejected():
    for lr in (0, -1, float("nan"), float("inf"), 6, True):
        with pytest.raises(ValueError): validate_params(lr, 10)
    for it in (0, 5001, 1.5, True):
        with pytest.raises(ValueError): validate_params(0.5, it)
    for th in (0, 1, 1.5):
        with pytest.raises(ValueError): validate_params(0.5, 10, th)
    with pytest.raises(ValueError): validate_params(0.5, 10, 0.5, -0.1)
    for X, y in ((np.zeros((0, 3)), np.zeros(0)), (np.array([[np.nan, 1.0]]), np.array([1.0])), (np.ones((2, 2)), np.array([0.0, 2.0])), (np.ones((3, 2)), np.array([0.0, 1.0]))):
        with pytest.raises(ValueError): GDLogisticRegression(0.5, 10).fit(X, y)


def test_missing_features_are_handled_with_indicators():
    v = vectorize({k: None for k in ("supplier", "invoice", "date", "amount", "gstin")}, None, None, None)
    assert len(v) == len(FEATURES) and np.isfinite(v).all() and v[5:10] == [1.0] * 5 and v[:5] == [0.0] * 5


def test_train_test_split_is_separated_and_counts_add_up():
    sp = make_split(seed=11, n=120); ids = lambda k: set().union(*[t[4] for t in sp[k]])
    assert ids("train").isdisjoint(ids("test")) and sp["train"] and sp["test"]
    d = service.counts(service.dataset(7)); assert d["train_positive"] + d["train_negative"] == d["train_pairs"] and d["test_positive"] + d["test_negative"] == d["test_pairs"] and d["synthetic"]


def test_metric_formulas_and_zero_division():
    m = classification_metrics([1, 1, 0, 0], [0.9, 0.4, 0.6, 0.1])
    assert m == {"accuracy": 0.5, "precision": 0.5, "recall": 0.5, "f1": 0.5, "confusion_matrix": {"tn": 1, "fp": 1, "fn": 1, "tp": 1}}
    assert classification_metrics([1, 0], [0.1, 0.2])["precision"] == 0.0 and classification_metrics([1, 1, 0], [0.9, 0.8, 0.1], 0.95)["recall"] == 0.0


def test_training_service_is_real_and_deterministic():
    a, _ = service.train(0.5, 120, 0.5, 0.0, 7); b, _ = service.train(0.5, 120, 0.5, 0.0, 7)
    assert a["loss_history"] == b["loss_history"] and len(a["loss_history"]) == 121 and a["initial_loss"] > a["final_loss"] and a["status"] == "completed" and list(a["weights"]) == FEATURES
    tm = a["test_metrics"]["confusion_matrix"]; assert sum(tm.values()) == a["dataset"]["test_pairs"] and a["initial_loss"] == pytest.approx(np.log(2), abs=1e-5)


def test_model_probability_integration_does_not_change_rule_statuses():
    c = mk(); with_m = c.post("/api/demo").json(); without = c.post("/api/demo?use_model=false").json(); thr = with_m["model"]["threshold"]
    assert [r["status"] for r in with_m["rows"]] == [r["status"] for r in without["rows"]] and not any("model_probability" in r for r in without["rows"])
    paired = [r for r in with_m["rows"] if r["purchase"] and r["gstr"]]; assert paired
    for r in paired:
        p = r["model_probability"]; assert 0 <= p <= 1 and r["model_score"] == p and r["model_verdict"] == ("match" if p >= thr else "no match")
        assert r["model_disagrees"] == (r["status"] == "Matched" and p < thr) and "score" in r
    assert with_m["model"]["disagreements"] == sum(r["model_disagrees"] for r in paired)


def test_training_api_validation_activation_and_reset(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "ACTIVE", tmp_path / "active.json"); g = mk()
    r = g.post("/api/model/train", json={"iterations": 80, "learning_rate": 0.3, "threshold": 0.6, "l2": 0}).json()
    assert len(r["loss_history"]) == 81 and r["params"]["threshold"] == 0.6 and r["params"]["learning_rate"] == 0.3 and r["activated"] is False and r["dataset"]["synthetic"]
    assert g.post("/api/model/train", json={"iterations": 80, "learning_rate": 0.3, "threshold": 0.6, "l2": 0}).json()["loss_history"] == r["loss_history"]
    for bad in ({"learning_rate": 0}, {"iterations": 5001}, {"threshold": 1.5}, {"learning_rate": 99}, {"l2": -1}): assert g.post("/api/model/train", json=bad).status_code == 422
    assert g.post("/api/model/train", json={"activate": True, "iterations": 50}).status_code == 401 and g.post("/api/model/reset").status_code == 401
    u = mk(); u.post("/api/auth/signup", json={"email": "m@example.com", "password": "correct horse 42"})
    assert u.post("/api/model/train", json={"activate": True, "iterations": 60, "threshold": 0.7}).json()["activated"] is True
    assert "activated" in g.get("/api/model").json()["source"] and g.get("/api/model").json()["threshold"] == 0.7 and g.post("/api/demo").json()["model"]["threshold"] == 0.7
    assert u.post("/api/model/reset").status_code == 200 and g.get("/api/model").json()["source"] == "pre-trained default"
