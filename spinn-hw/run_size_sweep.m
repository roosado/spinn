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
%
%   The sample
%   ----------
%   Every ladder point is also measured on a 500-digit subset -- the first 50 of each
%   class, in the frozen order, the same 500 indices at every grid. That subset is what
%   the site's "Go larger" page ships, because the full 2,000 digits at five grids do
%   not fit in a page that makes no external request. Recording it here is what lets a
%   live number in a browser be compared against a recorded one computed on *the same
%   digits*.
%
%   The stochastic source's sample is the same realizations, not a second draw:
%   mc.sweep partitions seeds by ladder index from the same baseSeed, and
%   err.conductance_variation draws per device and not per sample, so re-running the
%   same ladder in the same order with .subset set evaluates the identical perturbed
%   arrays on 500 digits. That is what makes it a twin, and it is also why nothing
%   already recorded can move.
%
%   The pass mark is not restated for the sample. It is 95% of the *full* ideal, and a
%   sample number is a pointer rather than a verdict.

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
        results.sample = sampleAcrossLadders(handoff, results);
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
    ex.meanCellFraction = zeros(size(mags));

    for n = 1:numel(mags)
        R = mags(n);
        I = err.ir_drop_exact(V, G, R, h);
        ex.exactAcc(n) = model.crossbar(h, struct('currents', I)).accuracy;

        % What the array really multiplies by is the current out per volt in. Driving
        % one row at a time with the identity gives it directly, and dividing by the
        % conductance each cell was programmed to says how much of it survives: the
        % worst cell is the one furthest from both edges.
        Geff = err.ir_drop_exact(eye(nRows), G, R, h);
        [ex.worstCellFraction(n), ex.meanCellFraction(n)] = cellFractions(Geff, G);

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


function [worst, avg] = cellFractions(Geff, G)
%CELLFRACTIONS Geff/G over every cell of every rail: the smallest, and the mean.
%   The minimum is one cell -- the corner furthest from both edges -- and it is the
%   number the write-up quotes. The mean is recorded beside it because the browser
%   draws the whole map and a pin on one cell would not hold the other 13,519.
    f = Geff(:) ./ G(:);
    worst = min(f);
    avg = mean(f);
end


function s = sampleAcrossLadders(handoffPath, results)
%SAMPLEACROSSLADDERS Every ladder, measured again on the 500-digit sample.
%   The header explains why this exists and why the stochastic source's sample is
%   the same realizations rather than a second draw. The magnitudes are read back
%   out of RESULTS rather than restated, so the two passes cannot drift apart on a
%   ladder.
    N_STOCHASTIC = 20;      % must match run_error_budget's; asserted below
    PER_CLASS = 50;

    h = io.read_handoff(handoffPath);
    labels = h.test_set.labels(:);
    idx = sampleIndices(labels, PER_CLASS);

    assert(numel(results.joint.seeds) == N_STOCHASTIC, ...
        'sizeSweep:realizationCount', ...
        ['run_error_budget ran %d realizations and this sample pass assumes %d. ' ...
         'The sample would not be the same draws.'], ...
        numel(results.joint.seeds), N_STOCHASTIC);

    s.perClass = PER_CLASS;
    s.n = numel(idx);
    % 0-based, as the labels crossing the handoff are and as the browser indexes.
    s.indices = idx(:).' - 1;

    G = model.program(h);
    Vs = model.encode(h, h.test_set.images(:, :, idx));
    s.ideal = model.crossbar(h, struct('voltages', Vs, 'subset', idx)).accuracy;
    fprintf('  sample %d digits, ideal %.4f (full %.4f)\n', s.n, s.ideal, results.ideal);

    % -- source 1: stochastic, and the same twenty arrays as the full run ---
    m1 = results.sigma_g_rel.magnitudes(:).';
    acc = sweepOnSample(h, "sigma_g_rel", m1, idx, N_STOCHASTIC, results.baseSeed);
    s.sigma_g_rel = struct('magnitudes', m1, 'accMean', mean(acc, 2).', ...
                           'accStd', std(acc, 0, 2).');

    % -- sources 2 and 3: deterministic, so one realization is the answer ---
    % Asserted rather than assumed: the recorded spread over three realizations is
    % zero, which is what says a second one would report the same number.
    %
    % To a tolerance, not exactly. std() of three *identical* accuracies comes back
    % as 1.4e-16 at several magnitudes, because (x+x+x)/3 is not bitwise x and each
    % deviation from the mean is then one ulp rather than none. That is arithmetic on
    % a constant, not a realization that differed.
    DETERMINISTIC_TOL = 1e-12;
    spread = max([results.states_per_device.accStd, results.wire_resistance_ohm.accStd]);
    assert(spread < DETERMINISTIC_TOL, 'sizeSweep:deterministicVaries', ...
        ['A deterministic source recorded a spread of %g over its realizations, so one ' ...
         'realization cannot stand for them.'], spread);

    m2 = results.states_per_device.magnitudes(:).';
    acc = sweepOnSample(h, "states_per_device", m2, idx, 1, results.baseSeed);
    s.states_per_device = struct('magnitudes', m2, 'accMean', acc(:).');

    m3 = results.wire_resistance_ohm.magnitudes(:).';
    acc = sweepOnSample(h, "wire_resistance_ohm", m3, idx, 1, results.baseSeed);
    s.wire_resistance_ohm = struct('magnitudes', m3, 'accMean', acc(:).');

    % -- source 3 again, with the network solved ----------------------------
    exactAcc = zeros(size(m3));
    for n = 1:numel(m3)
        I = err.ir_drop_exact(Vs, G, m3(n), h);
        exactAcc(n) = model.crossbar(h, ...
            struct('currents', I, 'voltages', Vs, 'subset', idx)).accuracy;
    end
    s.exact = struct('magnitudes', m3, 'exactAcc', exactAcc);
end


function acc = sweepOnSample(h, key, mags, idx, nReal, baseSeed)
%SWEEPONSAMPLE One source over its recorded ladder, on the sample.
%   Same ladder, same order, same baseSeed as the full run, so mc.sweep's
%   partitioning hands each magnitude the seeds it handed the full run.
    fprintf('  sample: %-22s %d magnitudes x %d realizations\n', key, numel(mags), nReal);
    cfgs = cell(1, numel(mags));
    for i = 1:numel(mags)
        cfgs{i} = struct(key, mags(i), 'subset', idx);
    end
    acc = mc.sweep(h, cfgs, nReal, baseSeed, @mc.run_montecarlo_crossbar);
end


function idx = sampleIndices(labels, perClass)
%SAMPLEINDICES The first PERCLASS of each class, in the frozen order.
%   Not a random 500: one index then means one digit at every grid, which is what
%   the page's "same digit at each size" strip needs, and the per-digit bars are
%   balanced rather than lopsided. Returned ascending, so the sample is the frozen
%   set in its own order with 1,500 digits left out.
    idx = [];
    for c = 0:9
        hits = find(labels == c);
        assert(numel(hits) >= perClass, 'sizeSweep:tooFewOfAClass', ...
            'Class %d has %d digits, fewer than the %d the sample takes.', ...
            c, numel(hits), perClass);
        idx = [idx; hits(1:perClass)]; %#ok<AGROW>
    end
    idx = sort(idx);
end


function v = pick(mags, idx)
    if isempty(idx), v = NaN; else, v = mags(idx); end
end
