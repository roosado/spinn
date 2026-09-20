function summary = run_size_sweep(grids, sizeDir)
%RUN_SIZE_SWEEP The error budget at each array size, and the first-order model checked.
%   SUMMARY = RUN_SIZE_SWEEP() runs run_error_budget on the array trained at each
%   image grid g in [6 8 12 18 26] -- 36 to 676 rows, ten columns throughout -- and
%   writes exports/size/g<gg>/error_budget.json beside each handoff. SUMMARY is a
%   table of what was run.
%
%   Declared before it was run, in docs/history.md (2026-09-19): the sizes, the seeds,
%   the ladder below, the pass mark (95% of *each size's own* ideal) and what "the
%   size limit" means. Nothing here is chosen after the curves are seen.
%
%   Sources 1 and 2 use run_error_budget's own ladders, unchanged, and so do the
%   seeds: baseSeed 20260908 at every size, 20 realizations for the stochastic
%   source and 3 for the deterministic ones.
%
%   Source 3 uses the ladder 2*10^(k/3) ohm, k = -6..8. It has 2 and 20 ohm in it
%   exactly -- the per-cell wiring at 65 nm and at 7 nm (docs/comparison_row.md) -- so
%   "does cited wiring hold at this size" is read straight off a ladder point rather
%   than off an edge someone interpolated.
%
%   The exact check
%   ---------------
%   err.ir_drop is first order and one pass overstates the drop. The declaration said
%   the accuracy would also be computed with the drop solved, at each size's bracket,
%   and that where the two disagree the solved answer is the one carried. Both are
%   recorded here across the *whole* ladder, because a bracket cannot be carried
%   without the points either side of it.
%
%   The solve is err.ir_drop_exact, a direct solve of the resistive network. A first
%   version iterated the first-order model to a fixed point instead; it agreed
%   wherever it converged and did not converge at exactly the resistances the edge
%   sits between, so it was replaced rather than tuned.
%
%   It is a check and is not swapped into the driver: the recorded error budget, the
%   row and the browser's copy of this arithmetic are all first order.

    arguments
        grids (1,:) double = [6 8 12 18 26]
        sizeDir (1,1) string = "exports/size"
    end

    here = fileparts(mfilename('fullpath'));
    addpath(here);

    CITED_OHM = [2 20];             % 65 nm (Agrawal 2019) and 7 nm (Victor 2024)

    k = -6:8;
    ladder = 2 * 10 .^ (k / 3);

    summary = struct('grid', {}, 'rows', {}, 'ideal', {}, ...
                     'firstOrderLast', {}, 'firstOrderFirstFail', {}, ...
                     'exactLast', {}, 'exactFirstFail', {});

    for g = grids
        dir = sprintf("%s/g%02d", sizeDir, g);
        handoff = dir + "/crossbar_handoff.h5";
        out = dir + "/error_budget.json";
        fprintf('\n=== grid %dx%d (%d rows) ===\n', g, g, g * g);

        results = run_error_budget(handoff, out, WireLadder = ladder);

        % The array this run rebuilt must be the one it was told about.
        assert(results.nRows == g * g, ...
            'sizeSweep:wrongArray', '%s holds %d rows, expected %d', handoff, results.nRows, g * g);

        results.exact = exactAcrossLadder(handoff, results);
        results.grid = g;
        results.citedWireOhm = CITED_OHM;

        fid = fopen(out, 'w');
        fprintf(fid, '%s', jsonencode(results, 'PrettyPrint', true));
        fclose(fid);
        fprintf('wrote %s\n', out);

        w = results.wire_resistance_ohm;
        summary(end+1) = struct('grid', g, 'rows', results.nRows, 'ideal', results.ideal, ...
            'firstOrderLast', w.lastHolding, 'firstOrderFirstFail', w.firstFailing, ...
            'exactLast', results.exact.lastHolding, ...
            'exactFirstFail', results.exact.firstFailing); %#ok<AGROW>
    end
end


function ex = exactAcrossLadder(handoffPath, results)
%EXACTACROSSLADDER Source 3 at every ladder magnitude, with the network solved.
    h = io.read_handoff(handoffPath);
    G = model.program(h);
    V = model.encode(h, h.test_set.images);
    w = results.wire_resistance_ohm;
    threshold = results.threshold;

    mags = w.magnitudes(:).';
    nRows = size(G, 1);

    ex.magnitudes = mags;
    ex.firstOrderAcc = w.accMean(:).';
    ex.exactAcc = zeros(size(mags));
    ex.worstCellFraction = zeros(size(mags));

    for n = 1:numel(mags)
        R = mags(n);
        I = err.ir_drop_exact(V, G, R, h);
        ex.exactAcc(n) = model.crossbar(h, struct('currents', I)).accuracy;

        % What the array really multiplies by is the current out per volt in. Driving
        % one row at a time with the identity gives it directly, and dividing by the
        % conductance each cell was programmed to says how much of it survives: the
        % worst cell is the one furthest from both edges.
        Geff = err.ir_drop_exact(eye(nRows), G, R, h);
        ex.worstCellFraction(n) = worstFraction(Geff, G);

        fprintf('  %8.3g ohm   first order %.4f   exact %.4f   worst cell keeps %5.1f%%\n', ...
            R, ex.firstOrderAcc(n), ex.exactAcc(n), 100 * ex.worstCellFraction(n));
    end

    ex.threshold = threshold;
    ex.firstOrderHolds = ex.firstOrderAcc >= threshold;
    ex.exactHolds = ex.exactAcc >= threshold;
    ex.disagree = ex.firstOrderHolds ~= ex.exactHolds;

    % The bracket, by the rule sweepOne uses for every other source.
    lastIdx = find(ex.exactHolds, 1, 'last');
    firstFail = find(~ex.exactHolds, 1, 'first');
    ex.lastHolding = pick(mags, lastIdx);
    ex.firstFailing = pick(mags, firstFail);
    ex.bracketed = ~isempty(lastIdx) && ~isempty(firstFail);
    if ~ex.bracketed
        warning("sizeSweep:exactNotBracketed", ...
            ['The exact model does not bracket its edge on this ladder (last holding ' ...
             '%g, first failing %g). That is a property of the ladder, not a result.'], ...
            ex.lastHolding, ex.firstFailing);
    end
end


function f = worstFraction(Geff, G)
%WORSTFRACTION The smallest Geff/G over every cell of every rail.
    f = min(Geff(:) ./ G(:));
end


function v = pick(mags, idx)
    if isempty(idx), v = NaN; else, v = mags(idx); end
end
