function I = ir_drop(V, G, Rwire, handoff) %#ok<INUSD>
%IR_DROP Error source 3: the wires are not ideal conductors.
%   I = ERR.IR_DROP(V, G, RWIRE, HANDOFF) returns column currents
%   n-by-nCols-by-nDev, computed with a finite resistance RWIRE (ohms) in each
%   wire segment between adjacent cells.
%
%   **This is the crossbar's characteristic failure and it has no photonic
%   counterpart.** It is a systematic rather than a random draw, it depends on
%   *where in the array* a device sits, and -- the part that matters for the
%   comparison -- it **grows with array size**. A tolerance number quoted without
%   the array size beside it is meaningless for this source, which is why the size
%   is fixed and reported in the row.
%
%   photonn's err.thermal_crosstalk transfers conceptually and not at all in
%   implementation: that is a conv2 blur over a phase mask, and this is an
%   accumulation along a wire.
%
%   Geometry
%   --------
%   Row drivers sit at the column-1 edge; column sense amplifiers at the row-1
%   edge. The segment of a row wire before column j carries the current every cell
%   from j onward will draw, so the voltage delivered to a cell is its driver
%   voltage less the accumulated drop of all the segments before it. The column
%   wire does the same in the other direction, lifting the far end of the device
%   off the amplifier's virtual ground. A device therefore sees
%
%       Veff(i,j) = Vrow(i,j) - Vcol(i,j)
%
%   and the cells furthest from both edges are starved worst.
%
%   Approximation
%   -------------
%   **First order, and deliberately not iterated.** The drops are computed from
%   the currents the ideal voltages would draw, rather than solved
%   self-consistently -- the exact problem is a linear system, because a reduced
%   voltage draws less current, which reduces the drop. One pass therefore
%   *overstates* the drop, which is the safe direction for a tolerance study but is
%   not the same as being right, and it stops being a small error once the drop is
%   a sizeable fraction of the drive: past that point this model lets a cell's
%   voltage go negative, which no network of resistors can do.
%
%   err.ir_drop_exact solves the same network exactly. This function is what the
%   recorded error budget, the published row and the browser's copy of the
%   arithmetic use, so it stays as it is; the exact solve is what the array-size
%   sweep checks it against (docs/array_size.md).
%
%   Samples are independent, so the work is done in blocks of BLOCK. At a few
%   hundred rows and a few thousand samples a single nRows-by-nCols-by-n array is
%   over a hundred megabytes and this function holds about eight of them at once;
%   blocking changes nothing about the result, which is tested to be identical.
    if Rwire <= 0
        I = plainCurrents(V, G);
        return
    end

    BLOCK = 250;
    n = size(V, 1);
    nDev = size(G, 3);
    I = zeros(n, size(G, 2), nDev);

    for d = 1:nDev
        for first = 1:BLOCK:n
            idx = first:min(first + BLOCK - 1, n);
            I(idx, :, d) = railCurrents(V(idx, :), G(:, :, d), Rwire);
        end
    end
end


function I = railCurrents(V, Gd, Rwire)
%RAILCURRENTS One rail, one block of samples, first order.
    Vd = permute(V, [2 3 1]);                 % nRows-by-1-by-n, the drive
    I0 = Vd .* Gd;                            % nRows-by-nCols-by-n, zeroth order

    % Current in each row segment: everything from this column onward.
    Irow = flip(cumsum(flip(I0, 2), 2), 2);
    dropRow = Rwire * cumsum(Irow, 2);

    % Current in each column segment: everything from this row onward.
    Icol = flip(cumsum(flip(I0, 1), 1), 1);
    dropCol = Rwire * cumsum(Icol, 1);

    Veff = Vd - dropRow - dropCol;
    I = permute(sum(Veff .* Gd, 1), [3 2 1]);
end


function I = plainCurrents(V, G)
%PLAINCURRENTS The ideal sum, for Rwire = 0. Kept identical to model.crossbar's.
    nDev = size(G, 3);
    I = zeros(size(V, 1), size(G, 2), nDev);
    for d = 1:nDev
        I(:, :, d) = V * G(:, :, d);
    end
end
