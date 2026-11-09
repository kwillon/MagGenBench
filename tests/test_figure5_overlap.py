import numpy as np
import pytest

from mvpipeline.analysis.figure5_overlap import (
    SlicedW1, bin_indices, common_edges, fixed_directions, histogram_mass,
    load_population, overlap, standardize,
)


def test_overlap_known_values_and_normalization():
    p = histogram_mass(np.array([0,0,1,1]), 4)
    q = histogram_mass(np.array([0,2]), 4)
    assert p.sum() == q.sum() == 1
    assert overlap(p,p) == 1
    assert overlap(p,q) == overlap(q,p) == .5
    assert overlap(np.array([1,0]),np.array([0,1])) == 0


def test_grid_retains_endpoints_and_shifted_support():
    x = np.array([[0.,0.],[1.,1.],[.5,.5]])
    for shifted in (False,True):
        edges=common_edges(x,10,shifted)
        idx=bin_indices(x,edges)
        hist=histogram_mass(idx,(len(edges[0])-1)*(len(edges[1])-1))
        assert hist.sum() == 1
        assert np.count_nonzero(hist) == 3
    with pytest.raises(ValueError,match="excludes"):
        bin_indices(np.array([[-1.,0.]]),common_edges(x,10))


def test_standardization_pooled_ddof_zero():
    x=np.array([[1.,2.],[3.,6.],[8.,9.]])
    z,mean,std=standardize(x)
    np.testing.assert_allclose(z.mean(axis=0),0,atol=1e-15)
    np.testing.assert_allclose(z.std(axis=0),1)
    np.testing.assert_allclose(z*std+mean,x)


def test_sliced_w1_exact_unequal_sizes_and_weights():
    # 1D supports 0,2 vs 1,3,4; integral |F-G| = 5/3.
    x=np.array([[0.,0.],[2.,0.]])
    y=np.array([[1.,0.],[3.,0.],[4.,0.]])
    axes=np.array([[1.,0.],[0.,1.]])
    assert SlicedW1(x,y,axes)() == pytest.approx(5/6)
    assert SlicedW1(y,x,axes)() == pytest.approx(5/6)
    assert SlicedW1(x,x,axes)() == pytest.approx(0)
    wx,wy=np.array([2,1]),np.array([0,1,2])
    expanded_x=np.repeat(x,wx,axis=0)
    expanded_y=np.repeat(y,wy,axis=0)
    assert SlicedW1(x,y,axes)(wx,wy) == pytest.approx(SlicedW1(expanded_x,expanded_y,axes)())


def test_fixed_directions_and_translation_oracle():
    directions=fixed_directions()
    np.testing.assert_array_equal(directions,fixed_directions())
    np.testing.assert_allclose(np.linalg.norm(directions,axis=1),1)
    x=np.zeros((3,2))
    delta=np.array([2.,-1.])
    assert SlicedW1(x,x+delta,directions)() == pytest.approx(np.abs(directions@delta).mean())


def test_exact_publication_population():
    raw,paired=load_population()
    assert len(raw) == 12281 and len(paired) == 12277
    assert paired.groupby('family').size().to_dict() == {
        'MatterGen':3033,'Con-CDVAE':3163,'CrystalFormer':2460,'CrystaLLM':314,'Crys-JEPA':3307}


def test_histogram_matches_numpy_with_bootstrap_multiplicities():
    rng = np.random.default_rng(1984)
    x = rng.normal(size=(137, 2))
    weights = rng.multinomial(len(x), np.full(len(x), 1 / len(x)))
    for bins in (10, 15, 20):
        edges = common_edges(x, bins)
        actual = histogram_mass(bin_indices(x, edges), bins*bins, weights)
        expected, _, _ = np.histogram2d(x[:, 0], x[:, 1], bins=edges, weights=weights)
        np.testing.assert_allclose(actual, expected.ravel()/expected.sum())


def test_sliced_w1_against_independent_quantile_transport():
    # Equal atomic weights on expanded samples: compare inverse-CDF integrals
    # on an exact common rational probability grid, independently of CDF sorting.
    rng = np.random.default_rng(1984)
    x, y = rng.normal(size=(7, 2)), rng.normal(size=(11, 2))
    wx, wy = rng.multinomial(7, np.full(7, 1/7)), rng.multinomial(11, np.full(11, 1/11))
    directions = fixed_directions()
    xp = np.sort(np.repeat(x, wx, axis=0) @ directions.T, axis=0)
    yp = np.sort(np.repeat(y, wy, axis=0) @ directions.T, axis=0)
    expected = np.abs(np.repeat(xp, 11, axis=0) - np.repeat(yp, 7, axis=0)).mean()
    assert SlicedW1(x, y, directions)(wx, wy) == pytest.approx(expected)


def test_population_mismatch_and_duplicate_ids_stop(tmp_path):
    raw, _ = load_population()
    source = tmp_path / 'changed.csv'
    raw.iloc[:-1].to_csv(source, index=False)
    with pytest.raises(ValueError, match='STOP'):
        load_population(source)
    raw.loc[1, 'structure_id'] = raw.loc[0, 'structure_id']
    raw.to_csv(source, index=False)
    with pytest.raises(ValueError, match='duplicated structure_id'):
        load_population(source)
