import numpy as np
from numpy.testing import assert_array_equal, assert_allclose
from scipy.sparse import csr_matrix

from ef.field_solver import FieldSolver
from ef.inner_region import InnerRegion
from ef.config.components import BoundaryConditionsConf, SpatialMeshConf
from ef.config.components import Box


class TestFieldSolver:

    def test_eval_field_from_potential(self):
        mesh = SpatialMeshConf((1.5, 2, 1), (0.5, 1, 1)).make(BoundaryConditionsConf())
        mesh.potential = np.stack([np.array([[0., 0, 0],
                                             [1, 2, 3],
                                             [4, 3, 2],
                                             [4, 4, 4]]), np.zeros((4, 3))], -1)
        FieldSolver.eval_fields_from_potential(mesh)
        expected = np.array([[[[-2, 0, 0], [0, 0, 0]], [[-4, 0, 0], [0, 0, 0]], [[-6, 0, 0], [0, 0, 0]]],
                             [[[-4, -1, 1], [0, 0, 1]], [[-3, -1, 2], [0, 0, 2]], [[-2, -1, 3], [0, 0, 3]]],
                             [[[-3, 1, 4], [0, 0, 4]], [[-2, 1, 3], [0, 0, 3]], [[-1, 1, 2], [0, 0, 2]]],
                             [[[0, 0, 4], [0, 0, 4]], [[-2, 0, 4], [0, 0, 4]], [[-4, 0, 4], [0, 0, 4]]]])
        assert_array_equal(mesh.electric_field, expected)

    def test_global_index(self):
        double_index = list(FieldSolver.double_index(np.array((9, 10, 6))))
        for i in range(7):
            for j in range(8):
                for k in range(4):
                    n = i + j * 7 + k * 7 * 8
                    assert FieldSolver.global_index_in_matrix_to_node_ijk(n, 9, 10, 6) == (i + 1, j + 1, k + 1)
                    assert FieldSolver.node_ijk_to_global_index_in_matrix(i + 1, j + 1, k + 1, 9, 10, 6) == n
                    assert double_index[n] == (n, i + 1, j + 1, k + 1)
        assert list(FieldSolver.double_index(np.array((4, 5, 3)))) == [(0, 1, 1, 1),
                                                                       (1, 2, 1, 1),
                                                                       (2, 1, 2, 1),
                                                                       (3, 2, 2, 1),
                                                                       (4, 1, 3, 1),
                                                                       (5, 2, 3, 1)]

    def test_init_rhs(self):
        mesh = SpatialMeshConf((4, 3, 3)).make(BoundaryConditionsConf())
        solver = FieldSolver(mesh, [])
        solver.init_rhs_vector_in_full_domain(mesh)
        assert_array_equal(solver.rhs, np.zeros(3 * 2 * 2))

        mesh = SpatialMeshConf((4, 3, 3)).make(BoundaryConditionsConf(-2))
        solver = FieldSolver(mesh, [])
        solver.init_rhs_vector_in_full_domain(mesh)
        assert_array_equal(solver.rhs, [6, 4, 6, 6, 4, 6, 6, 4, 6, 6, 4, 6])  # what

        mesh = SpatialMeshConf((4, 4, 5)).make(BoundaryConditionsConf(-2))
        solver = FieldSolver(mesh, [])
        solver.init_rhs_vector_in_full_domain(mesh)
        assert_array_equal(solver.rhs, [6, 4, 6, 4, 2, 4, 6, 4, 6,
                                        4, 2, 4, 2, 0, 2, 4, 2, 4,
                                        4, 2, 4, 2, 0, 2, 4, 2, 4,
                                        6, 4, 6, 4, 2, 4, 6, 4, 6])  # what

        mesh = SpatialMeshConf((8, 12, 5), (2, 3, 1)).make(BoundaryConditionsConf(-1))
        solver = FieldSolver(mesh, [])
        solver.init_rhs_vector_in_full_domain(mesh)
        assert_array_equal(solver.rhs, [49, 40, 49, 45, 36, 45, 49, 40, 49,
                                        13, 4, 13, 9, 0, 9, 13, 4, 13,
                                        13, 4, 13, 9, 0, 9, 13, 4, 13,
                                        49, 40, 49, 45, 36, 45, 49, 40, 49])

        mesh = SpatialMeshConf((4, 6, 9), (1, 2, 3)).make(BoundaryConditionsConf())
        solver = FieldSolver(mesh, [])
        mesh.charge_density = np.array([[[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
                                        [[0, 0, 0, 0], [0, 1, 2, 0], [0, -1, 0, 0], [0, 0, 0, 0]],
                                        [[0, 0, 0, 0], [0, 3, 4, 0], [0, 0, -1, 0], [0, 0, 0, 0]],
                                        [[0, 0, 0, 0], [0, 5, 6, 0], [0, -1, 0, 0], [0, 0, 0, 0]],
                                        [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]])
        solver.init_rhs_vector_in_full_domain(mesh)
        assert_allclose(solver.rhs, -np.array([1, 3, 5, -1, 0, -1, 2, 4, 6, 0, -1, 0]) * np.pi * 4 * 36)

        mesh = SpatialMeshConf((4, 6, 9), (1, 2, 3)).make(BoundaryConditionsConf())
        solver = FieldSolver(mesh, [])
        region = InnerRegion('test', Box((1, 2, 3), (1, 2, 3)), 3)
        solver.init_rhs_vector(mesh, [region])
        assert_array_equal(solver.rhs, [3, 3, 0, 3, 3, 0, 3, 3, 0, 3, 3, 0])

    def test_zero_nondiag_inside_objects(self):
        mesh = SpatialMeshConf((4, 6, 9), (1, 2, 3)).make(BoundaryConditionsConf())
        solver = FieldSolver(mesh, [])
        region = InnerRegion('test', Box((1, 2, 3), (1, 2, 3)), 3)

        solver.A = csr_matrix(np.full((12, 12), 2))
        assert_array_equal(solver.A.toarray(), [[2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
                                                [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
                                                [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
                                                [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
                                                [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
                                                [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
                                                [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
                                                [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
                                                [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
                                                [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
                                                [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
                                                [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]])
        solver.zero_nondiag_for_nodes_inside_objects(mesh, [region])
        assert_array_equal(solver.A.toarray(), [[1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                                                [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                                                [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
                                                [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
                                                [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
                                                [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
                                                [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
                                                [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
                                                [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
                                                [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
                                                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
                                                [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]])

        # TODO: check algorithm if on-diagonal zeros should turn into ones
        solver.A = csr_matrix(np.array([[4, 0, 3, 0, 0, 0, 0, 2, 0, 0, 0, 0],
                                        [0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0],
                                        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                                        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                                        [0, 0, 0, 0, 4, 0, 0, 0, 0, 0, 0, 0],
                                        [0, 0, 2, 0, 0, 3, 0, 0, 0, 0, 0, 0],
                                        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                                        [0, 0, 2, 0, 0, 0, 0, 0, 0, 1, 0, 0],
                                        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3],
                                        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                                        [0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 6, 0],
                                        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]))
        solver.zero_nondiag_for_nodes_inside_objects(mesh, [region])
        assert_array_equal(solver.A.toarray(), [[1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                                                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                                                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                                                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                                                [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
                                                [0, 0, 2, 0, 0, 3, 0, 0, 0, 0, 0, 0],
                                                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                                                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                                                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3],
                                                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                                                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
                                                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]])

    def test_d2dx2(self):
        a = FieldSolver.construct_d2dx2_in_3d(5, 4, 4).toarray()
        assert_array_equal(a, [[-2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                               [1, -2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                               [0, 1, -2, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                               [0, 0, 0, -2, 1, 0, 0, 0, 0, 0, 0, 0],
                               [0, 0, 0, 1, -2, 1, 0, 0, 0, 0, 0, 0],
                               [0, 0, 0, 0, 1, -2, 0, 0, 0, 0, 0, 0],
                               [0, 0, 0, 0, 0, 0, -2, 1, 0, 0, 0, 0],
                               [0, 0, 0, 0, 0, 0, 1, -2, 1, 0, 0, 0],
                               [0, 0, 0, 0, 0, 0, 0, 1, -2, 0, 0, 0],
                               [0, 0, 0, 0, 0, 0, 0, 0, 0, -2, 1, 0],
                               [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, -2, 1],
                               [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, -2]])

    def test_d2dy2(self):
        a = FieldSolver.construct_d2dy2_in_3d(5, 4, 4).toarray()
        assert_array_equal(a, [[-2, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
                               [0, -2, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
                               [0, 0, -2, 0, 0, 1, 0, 0, 0, 0, 0, 0],
                               [1, 0, 0, -2, 0, 0, 0, 0, 0, 0, 0, 0],
                               [0, 1, 0, 0, -2, 0, 0, 0, 0, 0, 0, 0],
                               [0, 0, 1, 0, 0, -2, 0, 0, 0, 0, 0, 0],
                               [0, 0, 0, 0, 0, 0, -2, 0, 0, 1, 0, 0],
                               [0, 0, 0, 0, 0, 0, 0, -2, 0, 0, 1, 0],
                               [0, 0, 0, 0, 0, 0, 0, 0, -2, 0, 0, 1],
                               [0, 0, 0, 0, 0, 0, 1, 0, 0, -2, 0, 0],
                               [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, -2, 0],
                               [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, -2]])

    def test_d2dz2(self):
        a = FieldSolver.construct_d2dz2_in_3d(5, 4, 4).toarray()
        assert_array_equal(a, [[-2, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
                               [0, -2, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
                               [0, 0, -2, 0, 0, 0, 0, 0, 1, 0, 0, 0],
                               [0, 0, 0, -2, 0, 0, 0, 0, 0, 1, 0, 0],
                               [0, 0, 0, 0, -2, 0, 0, 0, 0, 0, 1, 0],
                               [0, 0, 0, 0, 0, -2, 0, 0, 0, 0, 0, 1],
                               [1, 0, 0, 0, 0, 0, -2, 0, 0, 0, 0, 0],
                               [0, 1, 0, 0, 0, 0, 0, -2, 0, 0, 0, 0],
                               [0, 0, 1, 0, 0, 0, 0, 0, -2, 0, 0, 0],
                               [0, 0, 0, 1, 0, 0, 0, 0, 0, -2, 0, 0],
                               [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, -2, 0],
                               [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, -2]])

    def test_construct_equation_matrix_full_domain(self):
        mesh = SpatialMeshConf((4, 6, 9), (1, 2, 3)).make(BoundaryConditionsConf())
        solver = FieldSolver(mesh, [])
        solver.construct_equation_matrix_in_full_domain(5, 4, 4, 1, 2, 3)
        d = -2 * (2 * 2 * 3 * 3 + 3 * 3 + 2 * 2)
        x = 2 * 2 * 3 * 3
        y = 3 * 3
        z = 2 * 2
        assert_array_equal(solver.A.toarray(), [[d, x, 0, y, 0, 0, z, 0, 0, 0, 0, 0],
                                                [x, d, x, 0, y, 0, 0, z, 0, 0, 0, 0],
                                                [0, x, d, 0, 0, y, 0, 0, z, 0, 0, 0],
                                                [y, 0, 0, d, x, 0, 0, 0, 0, z, 0, 0],
                                                [0, y, 0, x, d, x, 0, 0, 0, 0, z, 0],
                                                [0, 0, y, 0, x, d, 0, 0, 0, 0, 0, z],
                                                [z, 0, 0, 0, 0, 0, d, x, 0, y, 0, 0],
                                                [0, z, 0, 0, 0, 0, x, d, x, 0, y, 0],
                                                [0, 0, z, 0, 0, 0, 0, x, d, 0, 0, y],
                                                [0, 0, 0, z, 0, 0, y, 0, 0, d, x, 0],
                                                [0, 0, 0, 0, z, 0, 0, y, 0, x, d, x],
                                                [0, 0, 0, 0, 0, z, 0, 0, y, 0, x, d]])
