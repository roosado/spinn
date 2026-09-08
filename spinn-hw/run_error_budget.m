function results = run_error_budget(handoffPath, outPath)
%RUN_ERROR_BUDGET Sweep each as-built error source, then all of them together.
%   RESULTS = RUN_ERROR_BUDGET(HANDOFFPATH, OUTPATH) loads the handoff, sweeps
%   sources 1-3 independently over magnitude ladders, runs a joint configuration,
%   and writes RESULTS to OUTPATH as JSON.
%
%   Not inherited: photonn kept its run_error_budget at its own repo root and only
%   the shared harness came across. The harness is what matters -- mc.sweep,
%   mc.pack and the seed partitioning inside them -- and this is the thin driver
%   that assembles a budget out of it.
%
%   The pass mark and the array size were declared in docs/history.md before this
%   was ever run. Choosing what counts as failure after seeing the curves is how a
%   tolerance study becomes an argument.
%
%   Edges are read off the ladder as a bracket: the last magnitude that holds and
%   the first that fails. Nothing is interpolated, and mc.pack deliberately stores
%   no fitted crossing point.

    arguments
        handoffPath (1,1) string
        outPath (1,1) string = "exports/error_budget.json"
    end

    here = fileparts(mfilename('fullpath'));
    addpath(here);

    BASE_SEED = 20260908;
    N_STOCHASTIC = 20;
    N_DETERMINISTIC = 3;    % enough to show the variance is zero, not more

    h = io.read_handoff(handoffPath);

    % Guard before anything else: if the as-built model cannot reproduce the ideal
    % at zero error, every number below describes a different array than the one
    % that was trained.
    ideal = model.crossbar(h).accuracy;
    if abs(ideal - h.test_acc) > 1e-12
        error("budget:idealMismatch", ...
            ['As-built ideal is %.6f but the handoff records %.6f. The array was ' ...
             'reconstructed wrongly; fix that before measuring its tolerance.'], ...
            ideal, h.test_acc);
    end
    threshold = 0.95 * ideal;

    fprintf('ideal %.4f, pass mark %.4f (95%%), array %dx%d, %d devices\n', ...
        ideal, threshold, h.geometry.n_rows, h.geometry.n_cols, ...
        h.geometry.n_rows * h.geometry.n_cols * h.geometry.devices_per_weight);

    results = struct();
    results.ideal = ideal;
    results.threshold = threshold;
    results.baseSeed = BASE_SEED;
    results.nRows = h.geometry.n_rows;
    results.nCols = h.geometry.n_cols;
    results.nDevices = h.geometry.n_rows * h.geometry.n_cols * h.geometry.devices_per_weight;
    results.scheme = h.scheme;

    % -- source 1: conductance variation, stochastic -----------------------
    % Logarithmic, because the reporting unit is log2(range/sigma): an evenly
    % spaced ladder in sigma is an unevenly spaced one in bits.
    mags1 = [0.002 0.005 0.010 0.020 0.035 0.050 0.075 0.100 0.150 0.200 0.300];
    results.sigma_g_rel = sweepOne(h, "sigma_g_rel", mags1, N_STOCHASTIC, ...
                                   BASE_SEED, threshold);

    % -- source 2: resolvable states, deterministic ------------------------
    % Descending, so "more error" runs left to right like the others.
    mags2 = [65 33 17 9 7 5 4 3 2];
    results.states_per_device = sweepOne(h, "states_per_device", mags2, ...
                                         N_DETERMINISTIC, BASE_SEED, threshold);

    % -- source 3: IR drop, deterministic ----------------------------------
    % UNSOURCED, so the ladder is chosen to bracket rather than to model a real
    % wire: a device is ~1/g_min ohms, and the drop starts to matter when the
    % accumulated wire resistance along a line approaches that.
    mags3 = [1e1 1e2 3e2 1e3 3e3 1e4 3e4 1e5 3e5];
    results.wire_resistance_ohm = sweepOne(h, "wire_resistance_ohm", mags3, ...
                                           N_DETERMINISTIC, BASE_SEED, threshold);

    % -- joint --------------------------------------------------------------
    % Each source set to the last magnitude it individually held at. If the
    % sources are independent, the joint accuracy drop should be close to the sum
    % of the individual drops; a joint result meaningfully worse is a real finding
    % about the crossbar rather than something to expect.
    joint = struct();
    names = ["sigma_g_rel", "states_per_device", "wire_resistance_ohm"];
    for n = names
        joint.(n) = results.(n).lastHolding;
    end
    fprintf('joint: sigma %.3f, states %d, wire %g ohm\n', ...
        joint.sigma_g_rel, joint.states_per_device, joint.wire_resistance_ohm);

    st = mc.run_montecarlo_crossbar(h, joint, N_STOCHASTIC, BASE_SEED + 9000);
    results.joint.config = joint;
    results.joint.mean = st.mean;
    results.joint.std = st.std;
    results.joint.seeds = st.seeds(:).';
    results.joint.drop = ideal - st.mean;
    results.joint.sumOfIndependentDrops = ...
        sum(arrayfun(@(n) ideal - results.(n).meanAtLastHolding, names));
    results.joint.holds = st.mean >= threshold;

    fprintf('joint mean %.4f (drop %.4f vs sum of independents %.4f)\n', ...
        st.mean, results.joint.drop, results.joint.sumOfIndependentDrops);

    % -- the binding source --------------------------------------------------
    % Whichever fails at the smallest fraction of its own swept range is not a
    % meaningful comparison across sources with different units, so the binding
    % source is named by judgement in the write-up rather than computed here.
    % What is computed is each source's bracket, which is what that judgement
    % needs.

    txt = jsonencode(results, 'PrettyPrint', true);
    fid = fopen(outPath, 'w');
    fprintf(fid, '%s', txt);
    fclose(fid);
    fprintf('wrote %s\n', outPath);
end


function s = sweepOne(h, key, mags, nReal, baseSeed, threshold)
%SWEEPONE One source, over its ladder, packed and bracketed.
    fprintf('  %-22s %d magnitudes x %d realizations\n', key, numel(mags), nReal);

    cfgs = cell(1, numel(mags));
    for i = 1:numel(mags)
        cfgs{i} = struct(key, mags(i));
    end

    acc = mc.sweep(h, cfgs, nReal, baseSeed, @mc.run_montecarlo_crossbar);
    packed = mc.pack(mags, acc, threshold);

    s.magnitudes = packed.magnitudes;
    s.accMean = packed.accMean;
    s.accStd = packed.accStd;
    s.threshold = packed.threshold;

    % The bracket. holds(i) is true where the mean is at or above the pass mark.
    holds = packed.accMean >= threshold;
    s.holds = holds;
    lastIdx = find(holds, 1, 'last');
    firstFail = find(~holds, 1, 'first');

    if isempty(lastIdx)
        s.lastHolding = NaN;
        s.meanAtLastHolding = NaN;
        s.bracketed = false;
        warning("budget:neverHolds", ...
            "%s fails at every magnitude on this ladder; the ladder starts too high.", key);
    else
        s.lastHolding = mags(lastIdx);
        s.meanAtLastHolding = packed.accMean(lastIdx);
        s.bracketed = ~isempty(firstFail);
    end

    if isempty(firstFail)
        s.firstFailing = NaN;
        warning("budget:neverFails", ...
            ['%s holds at every magnitude on this ladder, so no edge was found. ' ...
             'That is a property of the ladder, not a result -- widen it.'], key);
    else
        s.firstFailing = mags(firstFail);
    end
end
