import numpy as np
import pytest

from pandas._libs.tslibs.period import IncompatibleFrequency
import pandas.util._test_decorators as td

import pandas as pd
from pandas import (
    DataFrame,
    DatetimeIndex,
    Index,
    NaT,
    Period,
    PeriodIndex,
    Series,
    date_range,
    offsets,
    period_range,
)
from pandas.util import testing as tm

from ..datetimelike import DatetimeLike


class TestPeriodIndex(DatetimeLike):
    _holder = PeriodIndex

    @pytest.fixture(
        params=[
            tm.makePeriodIndex(10),
            period_range("20130101", periods=10, freq="D")[::-1],
        ],
        ids=["index_inc", "index_dec"],
    )
    def indices(self, request):
        return request.param

    def create_index(self):
        return period_range("20130101", periods=5, freq="D")

    def test_pickle_compat_construction(self):
        pass

    @pytest.mark.parametrize("freq", ["D", "M", "A"])
    def test_pickle_round_trip(self, freq):
        idx = PeriodIndex(["2016-05-16", "NaT", NaT, np.NaN], freq=freq)
        result = tm.round_trip_pickle(idx)
        tm.assert_index_equal(result, idx)

    def test_where(self):
        # This is handled in test_indexing
        pass

    @pytest.mark.parametrize("use_numpy", [True, False])
    @pytest.mark.parametrize(
        "index",
        [
            pd.period_range("2000-01-01", periods=3, freq="D"),
            pd.period_range("2001-01-01", periods=3, freq="2D"),
            pd.PeriodIndex(["2001-01", "NaT", "2003-01"], freq="M"),
        ],
    )
    def test_repeat_freqstr(self, index, use_numpy):
        # GH10183
        expected = PeriodIndex([p for p in index for _ in range(3)])
        result = np.repeat(index, 3) if use_numpy else index.repeat(3)
        tm.assert_index_equal(result, expected)
        assert result.freqstr == index.freqstr

    def test_fillna_period(self):
        # GH 11343
        idx = pd.PeriodIndex(["2011-01-01 09:00", pd.NaT, "2011-01-01 11:00"], freq="H")

        exp = pd.PeriodIndex(
            ["2011-01-01 09:00", "2011-01-01 10:00", "2011-01-01 11:00"], freq="H"
        )
        tm.assert_index_equal(idx.fillna(pd.Period("2011-01-01 10:00", freq="H")), exp)

        exp = pd.Index(
            [
                pd.Period("2011-01-01 09:00", freq="H"),
                "x",
                pd.Period("2011-01-01 11:00", freq="H"),
            ],
            dtype=object,
        )
        tm.assert_index_equal(idx.fillna("x"), exp)

        exp = pd.Index(
            [
                pd.Period("2011-01-01 09:00", freq="H"),
                pd.Period("2011-01-01", freq="D"),
                pd.Period("2011-01-01 11:00", freq="H"),
            ],
            dtype=object,
        )
        tm.assert_index_equal(idx.fillna(pd.Period("2011-01-01", freq="D")), exp)

    def test_no_millisecond_field(self):
        msg = "type object 'DatetimeIndex' has no attribute 'millisecond'"
        with pytest.raises(AttributeError, match=msg):
            DatetimeIndex.millisecond

        msg = "'DatetimeIndex' object has no attribute 'millisecond'"
        with pytest.raises(AttributeError, match=msg):
            DatetimeIndex([]).millisecond

    @pytest.mark.parametrize("sort", [None, False])
    def test_difference_freq(self, sort):
        # GH14323: difference of Period MUST preserve frequency
        # but the ability to union results must be preserved

        index = period_range("20160920", "20160925", freq="D")

        other = period_range("20160921", "20160924", freq="D")
        expected = PeriodIndex(["20160920", "20160925"], freq="D")
        idx_diff = index.difference(other, sort)
        tm.assert_index_equal(idx_diff, expected)
        tm.assert_attr_equal("freq", idx_diff, expected)

        other = period_range("20160922", "20160925", freq="D")
        idx_diff = index.difference(other, sort)
        expected = PeriodIndex(["20160920", "20160921"], freq="D")
        tm.assert_index_equal(idx_diff, expected)
        tm.assert_attr_equal("freq", idx_diff, expected)

    def test_hash_error(self):
        index = period_range("20010101", periods=10)
        msg = "unhashable type: '{}'".format(type(index).__name__)
        with pytest.raises(TypeError, match=msg):
            hash(index)

    def test_make_time_series(self):
        index = period_range(freq="A", start="1/1/2001", end="12/1/2009")
        series = Series(1, index=index)
        assert isinstance(series, Series)

    def test_shallow_copy_empty(self):

        # GH13067
        idx = PeriodIndex([], freq="M")
        result = idx._shallow_copy()
        expected = idx

        tm.assert_index_equal(result, expected)

    def test_shallow_copy_i8(self):
        # GH-24391
        pi = period_range("2018-01-01", periods=3, freq="2D")
        result = pi._shallow_copy(pi.asi8, freq=pi.freq)
        tm.assert_index_equal(result, pi)

    def test_shallow_copy_changing_freq_raises(self):
        pi = period_range("2018-01-01", periods=3, freq="2D")
        msg = "specified freq and dtype are different"
        with pytest.raises(IncompatibleFrequency, match=msg):
            pi._shallow_copy(pi, freq="H")

    def test_dtype_str(self):
        pi = pd.PeriodIndex([], freq="M")
        with tm.assert_produces_warning(FutureWarning):
            assert pi.dtype_str == "period[M]"
            assert pi.dtype_str == str(pi.dtype)

        with tm.assert_produces_warning(FutureWarning):
            pi = pd.PeriodIndex([], freq="3M")
            assert pi.dtype_str == "period[3M]"
            assert pi.dtype_str == str(pi.dtype)

    def test_view_asi8(self):
        idx = pd.PeriodIndex([], freq="M")

        exp = np.array([], dtype=np.int64)
        tm.assert_numpy_array_equal(idx.view("i8"), exp)
        tm.assert_numpy_array_equal(idx.asi8, exp)

        idx = pd.PeriodIndex(["2011-01", pd.NaT], freq="M")

        exp = np.array([492, -9223372036854775808], dtype=np.int64)
        tm.assert_numpy_array_equal(idx.view("i8"), exp)
        tm.assert_numpy_array_equal(idx.asi8, exp)

        exp = np.array([14975, -9223372036854775808], dtype=np.int64)
        idx = pd.PeriodIndex(["2011-01-01", pd.NaT], freq="D")
        tm.assert_numpy_array_equal(idx.view("i8"), exp)
        tm.assert_numpy_array_equal(idx.asi8, exp)

    def test_values(self):
        idx = pd.PeriodIndex([], freq="M")

        exp = np.array([], dtype=np.object)
        tm.assert_numpy_array_equal(idx.values, exp)
        tm.assert_numpy_array_equal(idx.to_numpy(), exp)
        with tm.assert_produces_warning(FutureWarning):
            tm.assert_numpy_array_equal(idx.get_values(), exp)
        exp = np.array([], dtype=np.int64)
        tm.assert_numpy_array_equal(idx._ndarray_values, exp)

        idx = pd.PeriodIndex(["2011-01", pd.NaT], freq="M")

        exp = np.array([pd.Period("2011-01", freq="M"), pd.NaT], dtype=object)
        tm.assert_numpy_array_equal(idx.values, exp)
        tm.assert_numpy_array_equal(idx.to_numpy(), exp)
        exp = np.array([492, -9223372036854775808], dtype=np.int64)
        tm.assert_numpy_array_equal(idx._ndarray_values, exp)

        idx = pd.PeriodIndex(["2011-01-01", pd.NaT], freq="D")

        exp = np.array([pd.Period("2011-01-01", freq="D"), pd.NaT], dtype=object)
        tm.assert_numpy_array_equal(idx.values, exp)
        tm.assert_numpy_array_equal(idx.to_numpy(), exp)
        exp = np.array([14975, -9223372036854775808], dtype=np.int64)
        tm.assert_numpy_array_equal(idx._ndarray_values, exp)

    def test_period_index_length(self):
        pi = period_range(freq="A", start="1/1/2001", end="12/1/2009")
        assert len(pi) == 9

        pi = period_range(freq="Q", start="1/1/2001", end="12/1/2009")
        assert len(pi) == 4 * 9

        pi = period_range(freq="M", start="1/1/2001", end="12/1/2009")
        assert len(pi) == 12 * 9

        start = Period("02-Apr-2005", "B")
        i1 = period_range(start=start, periods=20)
        assert len(i1) == 20
        assert i1.freq == start.freq
        assert i1[0] == start

        end_intv = Period("2006-12-31", "W")
        i1 = period_range(end=end_intv, periods=10)
        assert len(i1) == 10
        assert i1.freq == end_intv.freq
        assert i1[-1] == end_intv

        end_intv = Period("2006-12-31", "1w")
        i2 = period_range(end=end_intv, periods=10)
        assert len(i1) == len(i2)
        assert (i1 == i2).all()
        assert i1.freq == i2.freq

        end_intv = Period("2006-12-31", ("w", 1))
        i2 = period_range(end=end_intv, periods=10)
        assert len(i1) == len(i2)
        assert (i1 == i2).all()
        assert i1.freq == i2.freq

        msg = "start and end must have same freq"
        with pytest.raises(ValueError, match=msg):
            period_range(start=start, end=end_intv)

        end_intv = Period("2005-05-01", "B")
        i1 = period_range(start=start, end=end_intv)

        msg = (
            "Of the three parameters: start, end, and periods, exactly two"
            " must be specified"
        )
        with pytest.raises(ValueError, match=msg):
            period_range(start=start)

        # infer freq from first element
        i2 = PeriodIndex([end_intv, Period("2005-05-05", "B")])
        assert len(i2) == 2
        assert i2[0] == end_intv

        i2 = PeriodIndex(np.array([end_intv, Period("2005-05-05", "B")]))
        assert len(i2) == 2
        assert i2[0] == end_intv

        # Mixed freq should fail
        vals = [end_intv, Period("2006-12-31", "w")]
        msg = r"Input has different freq=W-SUN from PeriodIndex\(freq=B\)"
        with pytest.raises(IncompatibleFrequency, match=msg):
            PeriodIndex(vals)
        vals = np.array(vals)
        with pytest.raises(ValueError, match=msg):
            PeriodIndex(vals)

    def test_fields(self):
        # year, month, day, hour, minute
        # second, weekofyear, week, dayofweek, weekday, dayofyear, quarter
        # qyear
        pi = period_range(freq="A", start="1/1/2001", end="12/1/2005")
        self._check_all_fields(pi)

        pi = period_range(freq="Q", start="1/1/2001", end="12/1/2002")
        self._check_all_fields(pi)

        pi = period_range(freq="M", start="1/1/2001", end="1/1/2002")
        self._check_all_fields(pi)

        pi = period_range(freq="D", start="12/1/2001", end="6/1/2001")
        self._check_all_fields(pi)

        pi = period_range(freq="B", start="12/1/2001", end="6/1/2001")
        self._check_all_fields(pi)

        pi = period_range(freq="H", start="12/31/2001", end="1/1/2002 23:00")
        self._check_all_fields(pi)

        pi = period_range(freq="Min", start="12/31/2001", end="1/1/2002 00:20")
        self._check_all_fields(pi)

        pi = period_range(
            freq="S", start="12/31/2001 00:00:00", end="12/31/2001 00:05:00"
        )
        self._check_all_fields(pi)

        end_intv = Period("2006-12-31", "W")
        i1 = period_range(end=end_intv, periods=10)
        self._check_all_fields(i1)

    def _check_all_fields(self, periodindex):
        fields = [
            "year",
            "month",
            "day",
            "hour",
            "minute",
            "second",
            "weekofyear",
            "week",
            "dayofweek",
            "dayofyear",
            "quarter",
            "qyear",
            "days_in_month",
        ]

        periods = list(periodindex)
        s = pd.Series(periodindex)

        for field in fields:
            field_idx = getattr(periodindex, field)
            assert len(periodindex) == len(field_idx)
            for x, val in zip(periods, field_idx):
                assert getattr(x, field) == val

            if len(s) == 0:
                continue

            field_s = getattr(s.dt, field)
            assert len(periodindex) == len(field_s)
            for x, val in zip(periods, field_s):
                assert getattr(x, field) == val

    def test_period_set_index_reindex(self):
        # GH 6631
        df = DataFrame(np.random.random(6))
        idx1 = period_range("2011/01/01", periods=6, freq="M")
        idx2 = period_range("2013", periods=6, freq="A")

        df = df.set_index(idx1)
        tm.assert_index_equal(df.index, idx1)
        df = df.set_index(idx2)
        tm.assert_index_equal(df.index, idx2)

    @pytest.mark.parametrize(
        "p_values, o_values, values, expected_values",
        [
            (
                [Period("2019Q1", "Q-DEC"), Period("2019Q2", "Q-DEC")],
                [Period("2019Q1", "Q-DEC"), Period("2019Q2", "Q-DEC"), "All"],
                [1.0, 1.0],
                [1.0, 1.0, np.nan],
            ),
            (
                [Period("2019Q1", "Q-DEC"), Period("2019Q2", "Q-DEC")],
                [Period("2019Q1", "Q-DEC"), Period("2019Q2", "Q-DEC")],
                [1.0, 1.0],
                [1.0, 1.0],
            ),
        ],
    )
    def test_period_reindex_with_object(
        self, p_values, o_values, values, expected_values
    ):
        # GH 28337
        period_index = PeriodIndex(p_values)
        object_index = Index(o_values)

        s = pd.Series(values, index=period_index)
        result = s.reindex(object_index)
        expected = pd.Series(expected_values, index=object_index)
        tm.assert_series_equal(result, expected)

    def test_factorize(self):
        idx1 = PeriodIndex(
            ["2014-01", "2014-01", "2014-02", "2014-02", "2014-03", "2014-03"], freq="M"
        )

        exp_arr = np.array([0, 0, 1, 1, 2, 2], dtype=np.intp)
        exp_idx = PeriodIndex(["2014-01", "2014-02", "2014-03"], freq="M")

        arr, idx = idx1.factorize()
        tm.assert_numpy_array_equal(arr, exp_arr)
        tm.assert_index_equal(idx, exp_idx)

        arr, idx = idx1.factorize(sort=True)
        tm.assert_numpy_array_equal(arr, exp_arr)
        tm.assert_index_equal(idx, exp_idx)

        idx2 = pd.PeriodIndex(
            ["2014-03", "2014-03", "2014-02", "2014-01", "2014-03", "2014-01"], freq="M"
        )

        exp_arr = np.array([2, 2, 1, 0, 2, 0], dtype=np.intp)
        arr, idx = idx2.factorize(sort=True)
        tm.assert_numpy_array_equal(arr, exp_arr)
        tm.assert_index_equal(idx, exp_idx)

        exp_arr = np.array([0, 0, 1, 2, 0, 2], dtype=np.intp)
        exp_idx = PeriodIndex(["2014-03", "2014-02", "2014-01"], freq="M")
        arr, idx = idx2.factorize()
        tm.assert_numpy_array_equal(arr, exp_arr)
        tm.assert_index_equal(idx, exp_idx)

    def test_is_(self):
        create_index = lambda: period_range(freq="A", start="1/1/2001", end="12/1/2009")
        index = create_index()
        assert index.is_(index)
        assert not index.is_(create_index())
        assert index.is_(index.view())
        assert index.is_(index.view().view().view().view().view())
        assert index.view().is_(index)
        ind2 = index.view()
        index.name = "Apple"
        assert ind2.is_(index)
        assert not index.is_(index[:])
        assert not index.is_(index.asfreq("M"))
        assert not index.is_(index.asfreq("A"))

        assert not index.is_(index - 2)
        assert not index.is_(index - 0)

    def test_contains(self):
        rng = period_range("2007-01", freq="M", periods=10)

        assert Period("2007-01", freq="M") in rng
        assert not Period("2007-01", freq="D") in rng
        assert not Period("2007-01", freq="2M") in rng

    def test_contains_nat(self):
        # see gh-13582
        idx = period_range("2007-01", freq="M", periods=10)
        assert pd.NaT not in idx
        assert None not in idx
        assert float("nan") not in idx
        assert np.nan not in idx

        idx = pd.PeriodIndex(["2011-01", "NaT", "2011-02"], freq="M")
        assert pd.NaT in idx
        assert None in idx
        assert float("nan") in idx
        assert np.nan in idx

    def test_periods_number_check(self):
        msg = (
            "Of the three parameters: start, end, and periods, exactly two"
            " must be specified"
        )
        with pytest.raises(ValueError, match=msg):
            period_range("2011-1-1", "2012-1-1", "B")

    def test_start_time(self):
        # GH 17157
        index = period_range(freq="M", start="2016-01-01", end="2016-05-31")
        expected_index = date_range("2016-01-01", end="2016-05-31", freq="MS")
        tm.assert_index_equal(index.start_time, expected_index)

    def test_end_time(self):
        # GH 17157
        index = period_range(freq="M", start="2016-01-01", end="2016-05-31")
        expected_index = date_range("2016-01-01", end="2016-05-31", freq="M")
        expected_index = expected_index.shift(1, freq="D").shift(-1, freq="ns")
        tm.assert_index_equal(index.end_time, expected_index)

    def test_index_duplicate_periods(self):
        # monotonic
        idx = PeriodIndex([2000, 2007, 2007, 2009, 2009], freq="A-JUN")
        ts = Series(np.random.randn(len(idx)), index=idx)

        result = ts[2007]
        expected = ts[1:3]
        tm.assert_series_equal(result, expected)
        result[:] = 1
        assert (ts[1:3] == 1).all()

        # not monotonic
        idx = PeriodIndex([2000, 2007, 2007, 2009, 2007], freq="A-JUN")
        ts = Series(np.random.randn(len(idx)), index=idx)

        result = ts[2007]
        expected = ts[idx == 2007]
        tm.assert_series_equal(result, expected)

    def test_index_unique(self):
        idx = PeriodIndex([2000, 2007, 2007, 2009, 2009], freq="A-JUN")
        expected = PeriodIndex([2000, 2007, 2009], freq="A-JUN")
        tm.assert_index_equal(idx.unique(), expected)
        assert idx.nunique() == 3

        idx = PeriodIndex([2000, 2007, 2007, 2009, 2007], freq="A-JUN", tz="US/Eastern")
        expected = PeriodIndex([2000, 2007, 2009], freq="A-JUN", tz="US/Eastern")
        tm.assert_index_equal(idx.unique(), expected)
        assert idx.nunique() == 3

    def test_shift(self):
        # This is tested in test_arithmetic
        pass

    @td.skip_if_32bit
    def test_ndarray_compat_properties(self):
        super().test_ndarray_compat_properties()

    def test_negative_ordinals(self):
        Period(ordinal=-1000, freq="A")
        Period(ordinal=0, freq="A")

        idx1 = PeriodIndex(ordinal=[-1, 0, 1], freq="A")
        idx2 = PeriodIndex(ordinal=np.array([-1, 0, 1]), freq="A")
        tm.assert_index_equal(idx1, idx2)

    def test_pindex_fieldaccessor_nat(self):
        idx = PeriodIndex(
            ["2011-01", "2011-02", "NaT", "2012-03", "2012-04"], freq="D", name="name"
        )

        exp = Index([2011, 2011, -1, 2012, 2012], dtype=np.int64, name="name")
        tm.assert_index_equal(idx.year, exp)
        exp = Index([1, 2, -1, 3, 4], dtype=np.int64, name="name")
        tm.assert_index_equal(idx.month, exp)

    def test_pindex_qaccess(self):
        pi = PeriodIndex(["2Q05", "3Q05", "4Q05", "1Q06", "2Q06"], freq="Q")
        s = Series(np.random.rand(len(pi)), index=pi).cumsum()
        # Todo: fix these accessors!
        assert s["05Q4"] == s[2]

    def test_pindex_multiples(self):
        with tm.assert_produces_warning(FutureWarning):
            pi = PeriodIndex(start="1/1/11", end="12/31/11", freq="2M")
        expected = PeriodIndex(
            ["2011-01", "2011-03", "2011-05", "2011-07", "2011-09", "2011-11"],
            freq="2M",
        )
        tm.assert_index_equal(pi, expected)
        assert pi.freq == offsets.MonthEnd(2)
        assert pi.freqstr == "2M"

        pi = period_range(start="1/1/11", end="12/31/11", freq="2M")
        tm.assert_index_equal(pi, expected)
        assert pi.freq == offsets.MonthEnd(2)
        assert pi.freqstr == "2M"

        pi = period_range(start="1/1/11", periods=6, freq="2M")
        tm.assert_index_equal(pi, expected)
        assert pi.freq == offsets.MonthEnd(2)
        assert pi.freqstr == "2M"

    def test_iteration(self):
        index = period_range(start="1/1/10", periods=4, freq="B")

        result = list(index)
        assert isinstance(result[0], Period)
        assert result[0].freq == index.freq

    def test_is_full(self):
        index = PeriodIndex([2005, 2007, 2009], freq="A")
        assert not index.is_full

        index = PeriodIndex([2005, 2006, 2007], freq="A")
        assert index.is_full

        index = PeriodIndex([2005, 2005, 2007], freq="A")
        assert not index.is_full

        index = PeriodIndex([2005, 2005, 2006], freq="A")
        assert index.is_full

        index = PeriodIndex([2006, 2005, 2005], freq="A")
        with pytest.raises(ValueError, match="Index is not monotonic"):
            index.is_full

        assert index[:0].is_full

    def test_with_multi_index(self):
        # #1705
        index = date_range("1/1/2012", periods=4, freq="12H")
        index_as_arrays = [index.to_period(freq="D"), index.hour]

        s = Series([0, 1, 2, 3], index_as_arrays)

        assert isinstance(s.index.levels[0], PeriodIndex)

        assert isinstance(s.index.values[0][0], Period)

    def test_convert_array_of_periods(self):
        rng = period_range("1/1/2000", periods=20, freq="D")
        periods = list(rng)

        result = pd.Index(periods)
        assert isinstance(result, PeriodIndex)

    def test_append_concat(self):
        # #1815
        d1 = date_range("12/31/1990", "12/31/1999", freq="A-DEC")
        d2 = date_range("12/31/2000", "12/31/2009", freq="A-DEC")

        s1 = Series(np.random.randn(10), d1)
        s2 = Series(np.random.randn(10), d2)

        s1 = s1.to_period()
        s2 = s2.to_period()

        # drops index
        result = pd.concat([s1, s2])
        assert isinstance(result.index, PeriodIndex)
        assert result.index[0] == s1.index[0]

    def test_pickle_freq(self):
        # GH2891
        prng = period_range("1/1/2011", "1/1/2012", freq="M")
        new_prng = tm.round_trip_pickle(prng)
        assert new_prng.freq == offsets.MonthEnd()
        assert new_prng.freqstr == "M"

    def test_map(self):
        # test_map_dictlike generally tests

        index = PeriodIndex([2005, 2007, 2009], freq="A")
        result = index.map(lambda x: x.ordinal)
        exp = Index([x.ordinal for x in index])
        tm.assert_index_equal(result, exp)

    def test_join_self(self, join_type):
        index = period_range("1/1/2000", periods=10)
        joined = index.join(index, how=join_type)
        assert index is joined

    def test_insert(self):
        # GH 18295 (test missing)
        expected = PeriodIndex(
            ["2017Q1", pd.NaT, "2017Q2", "2017Q3", "2017Q4"], freq="Q"
        )
        for na in (np.nan, pd.NaT, None):
            result = period_range("2017Q1", periods=4, freq="Q").insert(1, na)
            tm.assert_index_equal(result, expected)

    @pytest.mark.parametrize(
        "msg, key",
        [
            (r"Period\('2019', 'A-DEC'\), 'foo', 'bar'", (Period(2019), "foo", "bar")),
            (r"Period\('2019', 'A-DEC'\), 'y1', 'bar'", (Period(2019), "y1", "bar")),
            (r"Period\('2019', 'A-DEC'\), 'foo', 'z1'", (Period(2019), "foo", "z1")),
            (
                r"Period\('2018', 'A-DEC'\), Period\('2016', 'A-DEC'\), 'bar'",
                (Period(2018), Period(2016), "bar"),
            ),
            (r"Period\('2018', 'A-DEC'\), 'foo', 'y1'", (Period(2018), "foo", "y1")),
            (
                r"Period\('2017', 'A-DEC'\), 'foo', Period\('2015', 'A-DEC'\)",
                (Period(2017), "foo", Period(2015)),
            ),
            (r"Period\('2017', 'A-DEC'\), 'z1', 'bar'", (Period(2017), "z1", "bar")),
        ],
    )
    def test_contains_raise_error_if_period_index_is_in_multi_index(self, msg, key):
        # issue 20684
        """
        parse_time_string return parameter if type not matched.
        PeriodIndex.get_loc takes returned value from parse_time_string as a tuple.
        If first argument is Period and a tuple has 3 items,
        process go on not raise exception
        """
        df = DataFrame(
            {
                "A": [Period(2019), "x1", "x2"],
                "B": [Period(2018), Period(2016), "y1"],
                "C": [Period(2017), "z1", Period(2015)],
                "V1": [1, 2, 3],
                "V2": [10, 20, 30],
            }
        ).set_index(["A", "B", "C"])
        with pytest.raises(KeyError, match=msg):
            df.loc[key]


def test_maybe_convert_timedelta():
    pi = PeriodIndex(["2000", "2001"], freq="D")
    offset = offsets.Day(2)
    assert pi._maybe_convert_timedelta(offset) == 2
    assert pi._maybe_convert_timedelta(2) == 2

    offset = offsets.BusinessDay()
    msg = r"Input has different freq=B from PeriodIndex\(freq=D\)"
    with pytest.raises(ValueError, match=msg):
        pi._maybe_convert_timedelta(offset)
