# (C) British Crown Copyright 2010 - 2014, Met Office
#
# This file is part of Iris.
#
# Iris is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Iris is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Iris.  If not, see <http://www.gnu.org/licenses/>.
"""
Test iris.util

"""
# import iris tests first so that some things can be initialised before
# importing anything else
import iris.tests as tests

import inspect
import os
import StringIO
import unittest

import numpy as np

import iris.analysis
import iris.coords
import iris.tests.stock as stock
import iris.util


class TestMonotonic(unittest.TestCase):
    def assertMonotonic(self, array, direction=None, **kwargs):
        if direction is not None:
            mono, dir = iris.util.monotonic(array, return_direction=True, **kwargs)
            if not mono:
                self.fail('Array was not monotonic:/n %r' % array)
            if dir != np.sign(direction):
                self.fail('Array was monotonic but not in the direction expected:'
                          '/n  + requested direction: %s/n  + resultant direction: %s' % (direction, dir))
        else:
            mono = iris.util.monotonic(array, **kwargs)
            if not mono:
                self.fail('Array was not monotonic:/n %r' % array)

    def assertNotMonotonic(self, array, **kwargs):
        mono = iris.util.monotonic(array, **kwargs)
        if mono:
            self.fail("Array was monotonic when it shouldn't be:/n %r" % array)

    def test_monotonic_pve(self):
        a = np.array([3, 4, 5.3])
        self.assertMonotonic(a)
        self.assertMonotonic(a, direction=1)

        # test the reverse for negative monotonic.
        a = a[::-1]
        self.assertMonotonic(a)
        self.assertMonotonic(a, direction=-1)

    def test_not_monotonic(self):
        b = np.array([3, 5.3, 4])
        self.assertNotMonotonic(b)

    def test_monotonic_strict(self):
        b = np.array([3, 5.3, 4])
        self.assertNotMonotonic(b, strict=True)
        self.assertNotMonotonic(b)

        b = np.array([3, 5.3, 5.3])
        self.assertNotMonotonic(b, strict=True)
        self.assertMonotonic(b, direction=1)
        
        b = b[::-1]
        self.assertNotMonotonic(b, strict=True)
        self.assertMonotonic(b, direction=-1)

        b = np.array([0.0])
        self.assertRaises(ValueError, iris.util.monotonic, b)
        self.assertRaises(ValueError, iris.util.monotonic, b, strict=True)

        b = np.array([0.0, 0.0])
        self.assertNotMonotonic(b, strict=True)
        self.assertMonotonic(b)


class TestReverse(unittest.TestCase):
    def test_simple(self):
        a = np.arange(12).reshape(3, 4)
        np.testing.assert_array_equal(a[::-1], iris.util.reverse(a, 0))
        np.testing.assert_array_equal(a[::-1, ::-1], iris.util.reverse(a, [0, 1]))
        np.testing.assert_array_equal(a[:, ::-1], iris.util.reverse(a, 1))
        np.testing.assert_array_equal(a[:, ::-1], iris.util.reverse(a, [1]))
        self.assertRaises(ValueError, iris.util.reverse, a, [])
        self.assertRaises(ValueError, iris.util.reverse, a, -1)
        self.assertRaises(ValueError, iris.util.reverse, a, 10)
        self.assertRaises(ValueError, iris.util.reverse, a, [-1])
        self.assertRaises(ValueError, iris.util.reverse, a, [0, -1])

    def test_single(self):
        a = np.arange(36).reshape(3, 4, 3)
        np.testing.assert_array_equal(a[::-1], iris.util.reverse(a, 0))
        np.testing.assert_array_equal(a[::-1, ::-1], iris.util.reverse(a, [0, 1]))
        np.testing.assert_array_equal(a[:, ::-1, ::-1], iris.util.reverse(a, [1, 2]))
        np.testing.assert_array_equal(a[..., ::-1], iris.util.reverse(a, 2))
        self.assertRaises(ValueError, iris.util.reverse, a, -1)
        self.assertRaises(ValueError, iris.util.reverse, a, 10)
        self.assertRaises(ValueError, iris.util.reverse, a, [-1])
        self.assertRaises(ValueError, iris.util.reverse, a, [0, -1])


class TestClipString(unittest.TestCase):
    def setUp(self):
        self.test_string = "Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."
        self.rider = "**^^**$$..--__" # A good chance at being unique and not in the string to be tested!

    def test_oversize_string(self):
        # Test with a clip length that means the string will be clipped

        clip_length = 109
        result = iris.util.clip_string(self.test_string, clip_length, self.rider)

        # Check the length is between what we requested ( + rider length) and the length of the original string
        self.assertTrue(clip_length + len(self.rider) <= len(result) < len(self.test_string), "String was not clipped.")

        # Also test the rider was added
        self.assertTrue(self.rider in result, "Rider was not added to the string when it should have been.")

    def test_undersize_string(self):
        # Test with a clip length that is longer than the string

        clip_length = 10999
        result = iris.util.clip_string(self.test_string, clip_length, self.rider)
        self.assertEqual(len(result), len(self.test_string), "String was clipped when it should not have been.")

        # Also test that no rider was added on the end if the string was not clipped
        self.assertFalse(self.rider in result, "Rider was adding to the string when it should not have been.")

    def test_invalid_clip_lengths(self):
        # Clip values less than or equal to zero are not valid
        for clip_length in [0, -100]:
            result = iris.util.clip_string(self.test_string, clip_length, self.rider)
            self.assertEqual(len(result), len(self.test_string), "String was clipped when it should not have been.")

    def test_default_values(self):
        # Get the default values specified in the function
        argspec = inspect.getargspec(iris.util.clip_string)
        arg_dict = dict(zip(argspec.args[-2:], argspec.defaults))

        result = iris.util.clip_string(self.test_string, arg_dict["clip_length"], arg_dict["rider"])

        self.assertLess(len(result), len(self.test_string), "String was not clipped.")

        rider_returned = result[-len(arg_dict["rider"]):]
        self.assertEquals(rider_returned, arg_dict["rider"], "Default rider was not applied.")

    def test_trim_string_with_no_spaces(self):

        clip_length = 200
        no_space_string = "a" * 500

        # Since this string has no spaces, clip_string will not be able to gracefully clip it
        # but will instead clip it exactly where the user specified
        result = iris.util.clip_string(no_space_string, clip_length, self.rider)

        expected_length = clip_length + len(self.rider)

        # Check the length of the returned string is equal to clip length + length of rider
        self.assertEquals(len(result), expected_length, "Mismatch in expected length of clipped string. Length was %s, expected value is %s" % (len(result), expected_length))
        

class TestDescribeDiff(iris.tests.IrisTest):
    def test_identical(self):
        test_cube_a = stock.realistic_4d()
        test_cube_b = stock.realistic_4d()

        return_str_IO = StringIO.StringIO()
        iris.util.describe_diff(test_cube_a, test_cube_b, output_file=return_str_IO)
        return_str = return_str_IO.getvalue()

        self.assertString(return_str, 'compatible_cubes.str.txt')

    def test_different(self):
        return_str_IO = StringIO.StringIO()
        
        # test incompatible attributes
        test_cube_a = stock.realistic_4d()
        test_cube_b = stock.realistic_4d()
        
        test_cube_a.attributes['Conventions'] = 'CF-1.5'
        test_cube_b.attributes['Conventions'] = 'CF-1.6'
        
        iris.util.describe_diff(test_cube_a, test_cube_b, output_file=return_str_IO)
        return_str = return_str_IO.getvalue()
        
        self.assertString(return_str, 'incompatible_attr.str.txt')
        
        # test incompatible names
        test_cube_a = stock.realistic_4d()
        test_cube_b = stock.realistic_4d()

        test_cube_a.standard_name = "relative_humidity"

        return_str_IO.truncate(0)
        iris.util.describe_diff(test_cube_a, test_cube_b, output_file=return_str_IO)
        return_str = return_str_IO.getvalue()

        self.assertString(return_str, 'incompatible_name.str.txt')

        # test incompatible unit
        test_cube_a = stock.realistic_4d()
        test_cube_b = stock.realistic_4d()
        
        test_cube_a.units = iris.unit.Unit('m')

        return_str_IO.truncate(0)
        iris.util.describe_diff(test_cube_a, test_cube_b, output_file=return_str_IO)
        return_str = return_str_IO.getvalue()
        
        self.assertString(return_str, 'incompatible_unit.str.txt')
        
        # test incompatible methods
        test_cube_a = stock.realistic_4d()
        test_cube_b = stock.realistic_4d().collapsed('model_level_number', iris.analysis.MEAN)

        return_str_IO.truncate(0)
        iris.util.describe_diff(test_cube_a, test_cube_b, output_file=return_str_IO)
        return_str = return_str_IO.getvalue()

        self.assertString(return_str, 'incompatible_meth.str.txt')

    def test_output_file(self):
        # test incompatible attributes
        test_cube_a = stock.realistic_4d()
        test_cube_b = stock.realistic_4d().collapsed('model_level_number', iris.analysis.MEAN)

        test_cube_a.attributes['Conventions'] = 'CF-1.5'
        test_cube_b.attributes['Conventions'] = 'CF-1.6'
        test_cube_a.standard_name = "relative_humidity"
        test_cube_a.units = iris.unit.Unit('m')

        with self.temp_filename() as filename:
            with open(filename, 'w') as f:
                iris.util.describe_diff(test_cube_a, test_cube_b, output_file=f)
                f.close()

            self.assertFilesEqual(filename,
                              'incompatible_cubes.str.txt')


class TestAsCompatibleShape(tests.IrisTest):
    def test_slice(self):
        cube = tests.stock.realistic_4d()
        sliced = cube[1, :, 2, :-2]
        expected = cube[1:2, :, 2:3, :-2]
        res = iris.util.as_compatible_shape(sliced, cube)
        self.assertEqual(res, expected)

    def test_transpose(self):
        cube = tests.stock.realistic_4d()
        transposed = cube.copy()
        transposed.transpose()
        expected = cube
        res = iris.util.as_compatible_shape(transposed, cube)
        self.assertEqual(res, expected)

    def test_slice_and_transpose(self):
        cube = tests.stock.realistic_4d()
        sliced_and_transposed = cube[1, :, 2, :-2]
        sliced_and_transposed.transpose()
        expected = cube[1:2, :, 2:3, :-2]
        res = iris.util.as_compatible_shape(sliced_and_transposed, cube)
        self.assertEqual(res, expected)

    def test_collapsed(self):
        cube = tests.stock.realistic_4d()
        collapsed = cube.collapsed('model_level_number', iris.analysis.MEAN)
        expected_shape = list(cube.shape)
        expected_shape[1] = 1
        expected_data = collapsed.data.reshape(expected_shape)
        res = iris.util.as_compatible_shape(collapsed, cube)
        self.assertCML(res, ('util', 'as_compatible_shape_collapsed.cml'),
                       checksum=False)
        self.assertArrayEqual(expected_data, res.data)
        self.assertArrayEqual(expected_data.mask, res.data.mask)

    def test_reduce_dimensionality(self):
        # Test that as_compatible_shape() can demote
        # length one dimensions to scalars.
        cube = tests.stock.realistic_4d()
        src = cube[:, 2:3]
        expected = reduced = cube[:, 2]
        res = iris.util.as_compatible_shape(src, reduced)
        self.assertEqual(res, expected)

    def test_anonymous_dims(self):
        cube = tests.stock.realistic_4d()
        # Move all coords from dim_coords to aux_coords.
        for coord in cube.dim_coords:
            dim = cube.coord_dims(coord)
            cube.remove_coord(coord)
            cube.add_aux_coord(coord, dim)

        sliced = cube[1, :, 2, :-2]
        expected = cube[1:2, :, 2:3, :-2]
        res = iris.util.as_compatible_shape(sliced, cube)
        self.assertEqual(res, expected)

    def test_scalar_auxcoord(self):
        def dim_to_aux(cube, coord_name):
            """Convert coordinate on cube from DimCoord to AuxCoord."""
            coord = cube.coord(coord_name)
            coord = iris.coords.AuxCoord.from_coord(coord)
            cube.replace_coord(coord)

        cube = tests.stock.realistic_4d()
        src = cube[:, :, 3]
        dim_to_aux(src, 'grid_latitude')
        expected = cube[:, :, 3:4]
        dim_to_aux(expected, 'grid_latitude')
        res = iris.util.as_compatible_shape(src, cube)
        self.assertEqual(res, expected)


if __name__ == '__main__':
    unittest.main()
