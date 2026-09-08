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
%   self-consistently -- the exact problem is a linear system per sample, because
%   a reduced voltage draws less current, which reduces the drop. One pass
%   therefore *overstates* the drop, which is the safe direction for a tolerance
%   study but is not the same as being right. Recorded here rather than left for a
%   reader to infer; iterating is the obvious refinement if this source turns out
%   to bind.
    if Rwire <= 0
        I = plainCurrents(V, G);
        return
    end

    nDev = size(G, 3);
    I = zeros(size(V, 1), size(G, 2), nDev);
    Vd = permute(V, [2 3 1]);                 % nRows-by-1-by-n

    for d = 1:nDev
        Gd = G(:, :, d);
        I0 = Vd .* Gd;                        % nRows-by-nCols-by-n, zeroth order

        % Current in each row segment: everything from this column onward.
        Irow = flip(cumsum(flip(I0, 2), 2), 2);
        dropRow = Rwire * cumsum(Irow, 2);

        % Current in each column segment: everything from this row onward.
        Icol = flip(cumsum(flip(I0, 1), 1), 1);
        dropCol = Rwire * cumsum(Icol, 1);

        Veff = Vd - dropRow - dropCol;
        I(:, :, d) = permute(sum(Veff .* Gd, 1), [3 2 1]);
    end
end


function I = plainCurrents(V, G)
%PLAINCURRENTS The ideal sum, for Rwire = 0. Kept identical to model.crossbar's.
    nDev = size(G, 3);
    I = zeros(size(V, 1), size(G, 2), nDev);
    for d = 1:nDev
        I(:, :, d) = V * G(:, :, d);
    end
end
