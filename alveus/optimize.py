import copy
import numpy as np
import numpy.linalg as la
from scipy.optimize import linprog  # TODO: REMOVE

from _errors import ConvergenceError


# ======================================================================================================================
# Root-finding Methods
# ======================================================================================================================
def secant(fun, x0, x1, args=()):
    # options ----------------------------------------------------------------------------------------------------------
    max_it = 1000
    tol = 1e-3

    # initializing loop ------------------------------------------------------------------------------------------------
    it = 0
    root = x1

    # iterating --------------------------------------------------------------------------------------------------------
    while abs(x1 - x0) > tol and it < max_it:
        f0 = fun(x0, *args)
        f1 = fun(x1, *args)
        root -= f1 * (root - x0) / (f1 - f0)

        if root in (np.inf, np.nan):
            raise ConvergenceError('division by zero')

        x0 = x1
        x1 = root
        it += 1

    return root


# ======================================================================================================================
# Least Squares Methods
# ======================================================================================================================
def residual(f, x, y, p, args=()):
    return y - f(x, *p, *args)


def lsq_obj(r):
    return 0.5 * la.norm(r) ** 2.


def d_lsq_obj(r, j):
    return j.T @ r


def jacobian_fd(x, p, f, args=()):
    m = len(p)
    j = [None for _ in range(0, m)]

    eps = 1e-8
    fx = f(x, *p, *args)

    for i in range(0, m):
        p_ = copy.deepcopy(list(p))
        p_[i] += eps
        j[i] = (f(x, *p_, *args) - fx) / eps

    return np.asarray(j).T


def nl_lsq(fun, x, y, p0, jac=None, args=()):
    # options ----------------------------------------------------------------------------------------------------------
    max_it = 1000
    max_it_bt = 100
    tol = 1e-3
    rho = 0.5
    c = 1e-4

    if jac is None:
        jac = lambda xj, *pj: jacobian_fd(xj, pj, fun, args=args)

    # initializing loop ------------------------------------------------------------------------------------------------
    it = 0
    converged = False
    p = p0
    res = residual(fun, x, y, p, args=args)
    j = jac(x, *p, *args)
    f = lsq_obj(res)
    df = d_lsq_obj(res, j)

    # iterating --------------------------------------------------------------------------------------------------------
    while not converged and it < max_it:
        # calculate optimized step
        try:

            q, r = la.qr(j)
            dp = la.solve(r, q.T @ res)

        except np.linalg.LinAlgError:
            raise ConvergenceError('Unable to find a solution due to singular matrix issues')

        # invoke backtracking
        alpha = 1.
        it_bt = 0

        p_bt = p + dp
        f_bt = lsq_obj(residual(fun, x, y, p_bt, args=args))
        csdf = -c * np.dot(dp, df)

        while f_bt >= (f + alpha * csdf) and it_bt < max_it_bt:
            p_bt = p + alpha * dp
            f_bt = lsq_obj(residual(fun, x, y, p_bt, args=args))

            alpha *= rho
            it_bt += 1

        p = p_bt

        # update parameters and check convergence
        res = residual(fun, x, y, p, args=args)
        f = lsq_obj(res)
        j = jac(x, *p_bt, *args)
        df = d_lsq_obj(res, j)

        if la.norm(df, np.inf) < tol:
            converged = True

        it += 1

    if it == max_it:
        raise ConvergenceError('Solver failed to converge within maximum number of iterations')

    return p


# ======================================================================================================================
# Linear Programming Methods
# ======================================================================================================================
def lin_ip(A, g, b):
    """
    TODO: NOT WORKING
    # Algorithm 14.3, Page 411 Nocedal & Wright

    Parameters
    ----------
    A : array_like
        system matrix of the constraints
    g : array_like
        objective function multiplier
    b : array_like
        right-hand side of the constrains

    Returns
    -------
    array_like
        optimal solution vector
    """

    converged = False
    m, n = A.shape
    max_iter = 10
    iter_ = 0
    eta = 0.99

    # initial value correction heuristic -------------------------------------------------------------------------------
    AA = A @ A.T
    x_t = A.T @ la.solve(AA, b)
    l_t = la.solve(AA, A @ g)
    s_t = g - A.T @ l_t

    dx = max(-1.5 * x_t.min(), 0.)
    ds = max(-1.5 * s_t.min(), 0.)
    x_h = x_t + dx
    s_h = s_t + ds

    xhsh = x_h.T @ s_h
    dx_h = .5 * xhsh / (np.sum(s_h))
    ds_h = .5 * xhsh / (np.sum(x_h))

    x = x_h + dx_h
    l = l_t
    s = s_h + ds_h

    # main loop --------------------------------------------------------------------------------------------------------
    r_c = A.T @ l + s - g
    r_b = A @ x - b
    mu = (x.T @ s) / n

    while (not converged) and (iter_ < max_iter):
        iter_ = iter_ + 1

        # KKT system
        kkt = np.block([[np.zeros((n, n)), A.T, np.eye(n)],
                        [A, np.zeros((m, m)), np.zeros((m, n))],
                        [np.diag(s.flatten()), np.zeros((n, m)), np.diag(x.flatten())]])

        rhs = np.vstack((-r_c, -r_b, -x * s))

        # Solving for and extracting affine variables
        # QR decompose KKT matrix, TODO: LDL decomposition instead
        q, r = la.qr(kkt)
        dv_aff = q @ la.solve(r.T, rhs)

        dx_aff = dv_aff[:n]
        ds_aff = dv_aff[(n + m):]

        # Determining indices and corresponding alpha for affine variables
        alpha_prim_aff = np.where(dx_aff < 0., -x / dx_aff, 1.).min()
        alpha_dual_aff = np.where(ds_aff < 0., -s / ds_aff, 1.).min()

        # Calculating affine mu, mu and sigma
        mu_aff = ((x + alpha_prim_aff * dx_aff).T @ (s + alpha_dual_aff * ds_aff)) / n
        sigma = (mu_aff / mu) ** 3. if mu > 1.e-10 else 0.

        rhs = np.vstack((-r_c, -r_b, -x * s - dx_aff * ds_aff + sigma * mu))

        # Solving for and extracting increments
        dv = q @ la.solve(r.T, rhs)
        dx = dv[:n]
        dl = dv[n:(n + m)]
        ds = dv[(n + m):]

        # Determining indices and corresponding alpha for x and s
        alpha_prim = np.where(dx < 0., eta * (-x / dx), 1.).min()
        alpha_dual = np.where(ds < 0., eta * (-s / ds), 1.).min()

        # updating x, l and s
        x += alpha_prim * dx
        l += alpha_dual * dl
        s += alpha_dual * ds

        print('X')
        print(x)

        # convergence check
        r_c = A.T @ l + s - g
        r_b = A @ x - b
        mu = (x.T @ s) / n

        converged = (la.norm(r_c, ord=np.inf) <= 1.e-9) and (la.norm(r_b, ord=np.inf) <= 1.e-9) and (abs(mu) <= 1.e-9)
        print('CONVERGENCE')
        print('rC', la.norm(r_c, ord=np.inf))
        print('rA', la.norm(r_b, ord=np.inf))
        print('mu', abs(mu))

    return x


# ======================================================================================================================
# Quadratic Programming Methods
# ======================================================================================================================
def nl_sqp(obj, con, x0, H0):
    """
    Non-linear SQP solver for inequality constrained problems
    TODO: Implement equality constraints
    :param obj:
    :param con:
    :param x0:
    :param H0:
    :return:
    """
    # Options ----------------------------------------------------------------------------------------------------------
    tol = 1.0e-3
    max_iter = 300
    n = x0.shape[0]

    # calculating objective function and constraint function using a numerical approximation for Jacobians
    xeval = x0
    f, df = obj(xeval)
    c, dc = con(xeval)

    m = c.size
    mu = 100.

    # assembling KKT system
    A = np.zeros((n + m, 0))  # incorrect, assemble for equality constraints
    b = np.zeros(0)  # incorrect, assemble for equality constraints
    H = np.block([[np.zeros(H0.shape), np.zeros((H0.shape[0], m))], [np.zeros((m, H0.shape[1])),  np.eye(m) * 1e-6]])
    g = np.block([np.zeros((df.shape[0], 1)), np.zeros((m, 1))])
    y = np.zeros(0)

    C = np.block([[np.zeros(dc.shape), np.zeros((m, m))], [np.zeros((m, n)), np.eye(m)]])
    d = np.zeros(2 * m)
    B = H0

    z = np.abs(la.solve(dc, df))
    s = np.ones(2 * m)
    dLold = df - dc @ z

    # Main loop iterations ---------------------------------------------------------------------------------------------
    converged = (la.norm(dLold, ord=np.inf) < tol) and (la.norm(z * c, ord=np.inf) < tol)  # z * c element wise

    rho = 0.5
    iter = 0

    while (not converged) and (iter < max_iter):
        # Updating initial guess input for the PDPCIP algorithm
        H[:n, :n] = B
        g = np.block([df, mu * np.ones(m)])
        # TODO: Missing the equality constrains here?
        C[:m, :m] = dc
        d[:m] = -c

        zpad = np.block([z, np.ones(m)])
        t = np.maximum(-(c + dc @ xeval), np.zeros(m))
        xt = np.block([xeval, t])

        # Sub problem: Solve constrained QP
        p, y, z, _ = quad_ip(H, g, A, b, C, d, xt, y, s, zpad)

        xeval = xt[:n]
        z = z[:n]
        p = p[:n]

        # Take step
        xeval += p

        # Function evaluation
        f, df = obj(xeval)
        c, dc = con(xeval)
        mu = (df.T @ p + 0.5 * p.T @ B @ p) / ((1. - rho) * la.norm(c, ord=1))

        # Lagrangian gradient, z used for inequality constraints
        dLnew = df - dc @ z

        # BFGS Hessian update
        q = dLnew - dLold
        Bp = B @ p

        if np.dot(p, q) >= 0.2 * np.dot(p, Bp):
            theta = 1.
        else:
            theta = (0.8 * np.dot(p, Bp)) / (np.dot(p, Bp) - np.dot(p, q))

        r = theta * q + (1. - theta) * Bp
        r = r.reshape((r.shape[0], 1))
        Bp = Bp.reshape((Bp.shape[0], 1))
        B += r @ r.T / np.dot(p, r) - Bp @ Bp.T / np.dot(p, Bp)

        dLold = dLnew
        iter += 1
        converged = (la.norm(dLold, np.inf) < tol) and (la.norm(z * c, np.inf) < tol)  # z * c piecewise

    info = converged
    zopt = z[:2]
    xopt = xeval
    return xopt, zopt, info


def quad_ip(H, g, A, b, C, d, x0, y0, s0, z0):
    """
    Primal Dual Predictor Corrector Interior Point Algorithm.
    :param H: 
    :param g: 
    :param A: 
    :param b: 
    :param C: 
    :param d:
    :param x0:
    :param y0:
    :param s0:
    :param z0:
    :return: 
    """
    # Options ----------------------------------------------------------------------------------------------------------
    epsilon = 1e-3
    max_iter = 100

    # Heuristic for initial point --------------------------------------------------------------------------------------
    mc = z0.size
    KKT0 = np.zeros((A.shape[1], A.shape[1]))

    rL = H @ x0 + g - A @ y0 - C @ z0
    rA = b - A.T @ x0
    rC = s0 + d - C.T @ x0
    rsz = s0 * z0  # element-wise

    # assemble KKT matrix
    H0 = H + (C @ np.diag((z0 / s0)) @ C.T)  # z0 / s0 element wise
    KKT = np.block([[H0, -A], [-A.T, KKT0]])

    # assemble RHS of KKT system
    rL0 = rL - C @ np.diag((z0 / s0)) @ (rC - rsz / z0)  # z0 / s0 and rsz. / z0 elementwise
    RHS = -np.block([rL0, rA])

    # QR decompose KKT matrix, TODO: LDL decomposition instead
    Q, R = la.qr(KKT)
    affvec = Q @ la.solve(R.T, RHS)

    xaff = affvec[:x0.shape[0]].T
    zaff = -np.diag((z0 / s0)) @ C.T @ xaff + np.diag((z0 / s0)) @ (rC - rsz / z0)  # z0 / s0 and rsz / z0 element wise
    saff = -rsz / z0 - np.diag((s0 / z0)) @ zaff  # rsz / z0 and s0 / z0 element wise element wise

    x = x0
    y = y0
    z = np.maximum(np.ones(z0.shape), abs(z0 + zaff))
    s = np.maximum(np.ones(s0.shape), abs(s0 + saff))
    mu0 = np.dot(z, s) / mc
    zdivs = z / s  # element wise

    # Iterations -------------------------------------------------------------------------------------------------------
    rL = H @ x + g - A @ y - C @ z
    rA = b - A.T @ x
    rC = s + d - C.T @ x
    rsz = s * z  # element wise
    mu = mu0

    iter = 0
    converged = convergence_check(rL, rA, rC, mu0, mu0, H, g, A, b, C, d, epsilon)

    while (not converged) and (iter < max_iter):
        # assemble KKT matrix
        Hbar = H + (C @ np.diag(zdivs) @ C.T)
        KKT = np.block([[Hbar, -A], [-A.T, KKT0]])

        # assemble RHS of KKT system
        rLbar = rL - C @ np.diag(zdivs) @ (rC - rsz / z)  # rsz / z element wise
        RHS = np.block([-rLbar, -rA])

        # QR decompose KKT matrix, TODO: LDL decomposition instead
        # [L, D, p] = ldl(KKT, 'lower', 'vector')
        # affvec = zeros(1, numel(RHS))
        # affvec(p) = L'\(D\(L\RHS(p)))
        Q, R = la.qr(KKT)  # may need method='complete
        affvec = Q @ la.solve(R.T, RHS)

        xaff = affvec[:x.shape[0]].T
        zaff = - np.diag(zdivs) @ C.T @ xaff + np.diag(zdivs) @ (rC - rsz / z)  # rsz / z element wise
        saff = -(rsz / z) - np.diag(s / z) @ zaff  # rsz / z and s / z element wise

        alphaaff1 = np.where(zaff < 0., -z / zaff, 1.).min()  # z / zaff element wise
        alphaaff2 = np.where(saff < 0., -s / saff, 1.).min()  # s / saff element wise
        alphaaff = np.minimum(alphaaff1, alphaaff2)

        muaff = np.dot((z + alphaaff * zaff), (s + alphaaff * saff)) / mc
        sigma = (muaff / mu) ** 3.

        # assembling updated RHS of KKT system
        rszbar = rsz + saff * zaff - sigma * mu  # saff * zaff element wise
        rLbar = rL - C @ np.diag(zdivs) @ (rC - rszbar / z)  # rszbar / z element wise
        RHS = np.block([-rLbar, -rA])

        # TODO: LDL decomposition
        # vec = np.zeros(numel(RHS), 1)
        # vec(p) = L'\(D\(L\RHS(p)))
        vec = Q @ la.solve(R.T, RHS)

        # calculate step size
        dx = vec[:x.shape[0]]
        dy = vec[x.shape[0] + 1:]
        dz = -np.diag(zdivs) @ C.T  @ dx + np.diag(zdivs) @ (rC-rszbar / z)  # rszbar / z element wise
        ds = -rszbar / z - np.diag(s / z) @ dz  # rszbar / z and s / z element wise

        alpha1 = np.where(dz < 0., -z / dz, 1.).min()  # z / dz element wise
        alpha2 = np.where(ds < 0., -s / ds, 1.).min()  # s / ds element wise
        alpha = np.minimum(alpha1, alpha2)

        # updating estimator with calculated step-size
        alphabar = 0.995 * alpha
        x = x + dx * alphabar
        y = y + dy * alphabar
        z = z + dz * alphabar
        s = s + ds * alphabar

        rL = H @ x + g - A @ y - C @ z
        rA = b - A.T @ x
        rC = s + d - C.T @ x
        rsz = s * z  # element wise
        mu = np.dot(z, s) / mc
        zdivs = z / s  # element wise
        converged = convergence_check(rL, rA, rC, mu, mu0, H, g, A, b, C, d, epsilon)
        iter += 1

    if converged:
        xopt = x
        yopt = y
        zopt = z
        sopt = s
    else:
        xopt = []
        yopt = []
        zopt = []
        sopt = []

    return xopt, yopt, zopt, sopt


def convergence_check(rL, rA, rC, mu, mu0, H, g, A, b, C, d, tol):
    conv = False
    rAcheck = True
    rCcheck = True

    # KKT system
    kkt = np.block([H, g.reshape((g.shape[0], 1)), A, C])
    rLcheck = la.norm(rL, ord=np.inf) <= tol * np.maximum(1., la.norm(kkt, ord=np.inf))

    # equality constraints
    eq = np.block([A.T, b.reshape((b.shape[0], 1))])
    if eq.size:
        rAcheck = la.norm(rA, ord=np.inf) <= tol * np.maximum(1., la.norm(eq, ord=np.inf))

    # inequality constraints
    ineq = np.block([np.eye(d.size), d.reshape((d.shape[0], 1)), C.T])
    if ineq.size:
        rCcheck = la.norm(rC, ord=np.inf) <= tol * np.maximum(1., la.norm(ineq, ord=np.inf))

    muCheck = np.abs(mu) <= tol * 1e-2 * mu0

    if rLcheck and rAcheck and rCcheck and muCheck:
        conv = True

    return conv


# QUADRATIC TEST SCRIPT ------------------------------------------------------------------------------------------------
#def func(x, a, b, c):
#    return a * np.exp(-b * x) + c


#def func_jac(x, a, b, c):
#    return np.array([np.exp(-b * x), -a * x * np.exp(-b * x), np.repeat(1., x.size)]).T

#xdata = np.linspace(0, 4, 50)
#y = func(xdata, 2.5, 1.3, 0.5)
#np.random.seed(1729)
#y_noise = 0.2 * np.random.normal(size=xdata.size)
#ydata = y + y_noise
#p = nl_lsq(func, xdata, ydata, p0=np.asarray([1., 1., 1.]), jac=func_jac)


# LINEAR TEST SCRIPT ---------------------------------------------------------------------------------------------------
# n = 2                     # Number of variables and constraints (2 for contour plot)
# A = np.random.rand(n, n)  # Generating A
# k = 2                     # Index to put in zeros
#
# xp = abs(np.random.rand(n, 1))
# xp[k:] = np.zeros((xp.size-k, 1))
# sp = abs(np.random.rand(n, 1))
# sp[:k-1] = np.zeros((sp.size-k + 1, 1))
#
# lp = np.random.rand(n, 1)   # Generating lambda
#
# g = A.T @ lp + sp      # Computing g
# b = A @ xp             # Computing b

# problem from: https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html
# A = np.zeros((2, 2))
# A[0, :] = np.array([-3., 1.])
# A[1, :] = np.array([1., 2.])
#
#
# b = np.zeros((2, 1))
# b[0, 0] = 6.
# b[1, 0] = 4.
#
# g = np.zeros((2, 1))
# g[0, 0] = -1.
# g[1, 0] = 4.
#
# # Solving problem using Linear Programming Predictor-Correction IP algorithm
# x_opt = lin_ip(A, g, b)
# #print(x_opt)
# obj = g.T @ x_opt
# #print(obj)
# print('OPTIMUM')
# print(x_opt, obj)
#
# c = [-1, 4]
# A = [[-3, 1], [1, 2]]
# b = [6, 4]
# #x0_bounds = (None, None)
# #x1_bounds = (-3, None)
# res = linprog(c, A_ub=A, b_ub=b)#, bounds=[x0_bounds, x1_bounds])
# print(res)