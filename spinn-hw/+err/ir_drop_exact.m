function I = ir_drop_exact(V, G, Rwire, handoff) %#ok<INUSD>
%IR_DROP_EXACT Error source 3, solved: the resistive network itself.
%   I = ERR.IR_DROP_EXACT(V, G, RWIRE, HANDOFF) returns what err.ir_drop returns --
%   column currents n-by-nCols-by-nDev, for RWIRE ohms in each wire segment -- without
%   its first-order approximation.
%
%   The geometry is err.ir_drop's: row drivers at the column-1 edge, column sense
%   amplifiers at the row-1 edge holding their wires at ground, a segment of RWIRE
%   between neighbouring cells in both directions, and each cell a conductance from
%   its row-wire node to its column-wire node.
%
%   Why this is cheap
%   -----------------
%   Wires and devices together are a *linear* resistive network, so the column
%   currents are exactly a matrix product,
%
%       I = V * Geff,
%
%   where Geff (nRows-by-nCols) is the conductance the array really presents: the
%   current into amplifier j per volt on driver i. It depends on G and RWIRE and not
%   on the inputs, so it is found once per rail -- one sparse solve of the nodal
%   equations -- and applied to every sample. With RWIRE = 0 it is G itself, and the
%   difference G - Geff is the whole of the IR-drop error, in one matrix.
%
%   The nodal matrix is symmetric, so Geff is read off from the amplifier end: nCols
%   solves against one unit at each output, not nRows against one at each driver.
%
%   Units are scaled by RWIRE so that a wire segment is 1 and a device is RWIRE*G,
%   which keeps every entry of order one however large the ratio of conductances.
%   A one-cell array gives Geff = G / (1 + 2 RWIRE G), the series resistance a cell
%   and its two wire segments make; that case and a direct nodal solve of a small
%   array are tests, and err.ir_drop is the first-order expansion of this.
    if Rwire <= 0
        I = err.ir_drop(V, G, 0, handoff);
        return
    end

    nDev = size(G, 3);
    I = zeros(size(V, 1), size(G, 2), nDev);
    for d = 1:nDev
        I(:, :, d) = V * effectiveConductance(G(:, :, d), Rwire);
    end
end


function Geff = effectiveConductance(G, R)
%EFFECTIVECONDUCTANCE What the array multiplies by: amplifier current per driver volt.
    [N, M] = size(G);
    nn = N * M;
    [ii, jj] = ndgrid(1:N, 1:M);
    r = ii + (jj - 1) * N;              % the row-wire node at cell (i,j)
    c = nn + r;                         % the column-wire node at cell (i,j)
    dev = R * G;                        % a device, in units of one wire segment

    hasNextCol = jj < M;                % a row-wire segment ahead of this node
    hasNextRow = ii < N;                % a column-wire segment ahead of this node

    % Kirchhoff's current law at every node, divided through by 1/R. A row node has
    % the segment behind it (to the driver or the previous node), the one ahead if
    % there is one, and its device; a column node likewise, toward the amplifier.
    rows = [r(:);  c(:);  r(:);  c(:);  r(hasNextCol); r(hasNextCol) + N; c(hasNextRow); c(hasNextRow) + 1];
    cols = [r(:);  c(:);  c(:);  r(:);  r(hasNextCol) + N; r(hasNextCol); c(hasNextRow) + 1; c(hasNextRow)];
    vals = [1 + hasNextCol(:) + dev(:); ...
            1 + hasNextRow(:) + dev(:); ...
            -dev(:); -dev(:); ...
            -ones(nnz(hasNextCol), 1); -ones(nnz(hasNextCol), 1); ...
            -ones(nnz(hasNextRow), 1); -ones(nnz(hasNextRow), 1)];
    A = sparse(rows, cols, vals, 2 * nn, 2 * nn);

    % A unit at each amplifier's column-wire node. A drive of V_i enters at the row
    % node (i,1) as V_i/R, so Geff(i,j) is that node's entry of the solution, over R.
    E = sparse(c(1, :), 1:M, 1, 2 * nn, M);
    Y = A \ E;
    Geff = full(Y(r(:, 1), :)) / R;

    % A direct solve returns something whether or not it is right. The residual is
    % how a singular or hopeless matrix is told from a merely large one.
    residual = norm(A * Y - E, 1) / norm(E, 1);
    if residual > 1e-9
        error("err:ir_drop_exact:illConditioned", ...
            "The nodal solve left a relative residual of %.2g at Rwire = %g ohm.", ...
            residual, R);
    end
end
