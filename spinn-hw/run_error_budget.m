function results = run_error_budget(handoffPath, outPath, options)
%RUN_ERROR_BUDGET Sweep each as-built error source, then all of them together.
%   RESULTS = RUN_ERROR_BUDGET(HANDOFFPATH, OUTPATH) loads the handoff, sweeps
%   sources 1-3 independently over magnitude ladders, runs a joint configuration,
%   and writes RESULTS to OUTPATH as JSON. Source 1 is swept twice: as a uniform
%   sigma against the span (the required precision, in the hub's unit) and as area
%   variation (sigma/mu, the form imec measured, which the delivered spread is
%   judged against). The two are never combined.
%
%   Source 2 is also swept as write errors: with probability r a device
%   programmed to an intermediate level lands on a neighbouring one. That needs a
%   number of levels to land between, so it runs at the WriteStates option, and
%   records which. Like area variation it sits beside its source and is not
%   stacked into the joint run. The PassMark option replaces 95% of ideal with an
%   absolute accuracy for every source in the run (the calibrated variant is
%   judged against the row's own mark); the 95% is then recorded as ownPassMark.
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
        % Source 3's magnitudes, in ohms per segment. The default is the ladder the
        % published row was measured on, so calling this without the option
        % reproduces it exactly; run_size_sweep passes its own.
        options.WireLadder (1,:) double = [1e1 1e2 3e2 1e3 3e3 1e4 3e4 1e5 3e5]
        % Which sources to sweep. All of them by default. The window-ratio variants
        % (exports/ratio/) run the area source alone: under a multiplicative spread
        % only the ratio matters, and the other sources there would be numbers
        % nobody asked for. The joint run needs sources 1-3 and is skipped without.
        options.Sources (1,:) string = ["sigma_g_rel", "sigma_area_rel", ...
                                        "states_per_device", "wire_resistance_ohm", ...
                                        "write_error_rate"]
        % Source 2's write errors need a lattice to miss. The row runs it at 7, the
        % fewest levels it holds at; run_size_sweep passes 5, the delivered count.
        options.WriteStates (1,1) double = 7
        % An absolute pass mark for every source in this run. NaN, the default,
        % means 95% of this array's own ideal, as it always has.
        options.PassMark (1,1) double = NaN
    end

    here = fileparts(mfilename('fullpath'));
    addpath(here);

    BASE_SEED = 20260908;
    N_STOCHASTIC = 20;
    N_DETERMINISTIC = 3;    % enough to show the variance is zero, not more

    % Per-attempt chance that a write to an intermediate level misses, the best and
    % the worst of imec's four intermediate-level medians: switching probability
    % 0.611 and 0.505 (Doevenspeck et al., VLSI 2021, Fig. 11(a)), so a miss is 1
    % minus each. apps/report_row.py holds the same two numbers, and a test pins the
    % ladders equal.
    FAIL_BEST = 0.389;
    FAIL_WORST = 0.495;

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
    ownPassMark = 0.95 * ideal;
    if isnan(options.PassMark)
        threshold = ownPassMark;
        fprintf('ideal %.4f, pass mark %.4f (95%%), array %dx%d, %d devices\n', ...
            ideal, threshold, h.geometry.n_rows, h.geometry.n_cols, ...
            h.geometry.n_rows * h.geometry.n_cols * h.geometry.devices_per_weight);
    else
        threshold = options.PassMark;
        fprintf(['ideal %.4f, pass mark %.4f (given; 95%% of this ideal is %.4f), ' ...
                 'array %dx%d, %d devices\n'], ...
            ideal, threshold, ownPassMark, h.geometry.n_rows, h.geometry.n_cols, ...
            h.geometry.n_rows * h.geometry.n_cols * h.geometry.devices_per_weight);
    end

    results = struct();
    results.ideal = ideal;
    results.threshold = threshold;
    if ~isnan(options.PassMark)
        results.ownPassMark = ownPassMark;
    end
    results.baseSeed = BASE_SEED;
    results.nRows = h.geometry.n_rows;
    results.nCols = h.geometry.n_cols;
    results.nDevices = h.geometry.n_rows * h.geometry.n_cols * h.geometry.devices_per_weight;
    results.scheme = h.scheme;

    run = @(name) any(options.Sources == name);

    % -- source 1: conductance variation, stochastic -----------------------
    % Logarithmic, because the reporting unit is log2(range/sigma): an evenly
    % spaced ladder in sigma is an unevenly spaced one in bits.
    if run("sigma_g_rel")
        mags1 = [0.002 0.005 0.010 0.020 0.035 0.050 0.075 0.100 0.150 0.200 0.300];
        results.sigma_g_rel = sweepOne(h, "sigma_g_rel", mags1, N_STOCHASTIC, ...
                                       BASE_SEED, threshold);
    end

    % -- source 1, measured: area variation, stochastic ---------------------
    % sigma/mu, the quantity imec measured. 0.031 and 0.063 are on the ladder
    % because they are the delivered bracket -- imec's measurements at the two
    % pillar sizes either side of this design's (docs/history.md, 2026-10-04) -- so
    % "does the delivered spread hold" is read off a ladder point rather than off
    % an edge someone interpolated. That is how 2 and 20 ohm got onto the size
    % sweep's wire ladder.
    if run("sigma_area_rel")
        mags1b = [0.010 0.020 0.031 0.035 0.050 0.063 0.075 0.100 0.150];
        results.sigma_area_rel = sweepOne(h, "sigma_area_rel", mags1b, N_STOCHASTIC, ...
                                          BASE_SEED, threshold);
    end

    % -- source 2: resolvable states, deterministic ------------------------
    % Descending, so "more error" runs left to right like the others.
    if run("states_per_device")
        mags2 = [65 33 17 9 7 5 4 3 2];
        results.states_per_device = sweepOne(h, "states_per_device", mags2, ...
                                             N_DETERMINISTIC, BASE_SEED, threshold);
    end

    % -- source 2, written: write errors, stochastic -----------------------
    % A device programmed to an intermediate level lands on a neighbour with
    % probability r. It sits beside source 2 as area variation sits beside source 1,
    % so the numbering of sources 4-7 does not move. It is judged at WriteStates
    % levels and cannot run without them, so they are the base config of every
    % rung, and recorded so a reader knows which lattice the ladder was run on.
    if run("write_error_rate")
        mags2b = writeLadder(FAIL_BEST, FAIL_WORST);
        results.write_error_rate = sweepOne(h, "write_error_rate", mags2b, ...
            N_STOCHASTIC, BASE_SEED, threshold, ...
            struct('states_per_device', options.WriteStates));
        results.write_error_rate.states = options.WriteStates;
    end

    % -- source 3: IR drop, deterministic ----------------------------------
    % The ladder is chosen to bracket rather than to model one wire: a device is
    % ~1/g_min ohms, and the drop starts to matter when the accumulated wire
    % resistance along a line approaches that. Published crossbar wiring is 2-20
    % ohms per cell (docs/history.md, 2026-09-11), at the bottom of this ladder.
    if run("wire_resistance_ohm")
        mags3 = options.WireLadder;
        results.wire_resistance_ohm = sweepOne(h, "wire_resistance_ohm", mags3, ...
                                               N_DETERMINISTIC, BASE_SEED, threshold);
    end

    % The joint run is sources 1-3. Write errors, like area variation, are not stacked.
    names = ["sigma_g_rel", "states_per_device", "wire_resistance_ohm"];
    if ~all(arrayfun(run, names))
        writeResults(results, outPath);
        return
    end

    % -- joint --------------------------------------------------------------
    % Each source set to the last magnitude it individually held at. If the
    % sources are independent, the joint accuracy drop should be close to the sum
    % of the individual drops; a joint result meaningfully worse is a real finding
    % about the crossbar rather than something to expect.
    %
    % Sources 1-3 only. Area variation is the measured form of source 1, not a
    % fourth source, and stacking the two would count one spread twice.
    joint = struct();
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

    writeResults(results, outPath);
end


function writeResults(results, outPath)
    txt = jsonencode(results, 'PrettyPrint', true);
    fid = fopen(outPath, 'w');
    fprintf(fid, '%s', txt);
    fclose(fid);
    fprintf('wrote %s\n', outPath);
end


function mags = writeLadder(failBest, failWorst)
%WRITELADDER The write-error ladder, built here and nowhere else.
%   A coarse base, plus failBest^m and failWorst^m for m = 1..6: the chance a write
%   still misses after m verified attempts, at the best and the worst intermediate
%   level. "The bracket after m attempts" is then read off two ladder points rather
%   than off an edge someone interpolated. Rounded to six places so that this side
%   and apps/report_row.py agree to the bit once the ladder has crossed through JSON.
    base = [1e-4 3e-4 1e-3 3e-3 1e-2 3e-2 0.1 0.3];
    m = 1:6;
    mags = unique([base, round(failBest .^ m, 6), round(failWorst .^ m, 6)]);
end


function s = sweepOne(h, key, mags, nReal, baseSeed, threshold, baseCfg)
%SWEEPONE One source, over its ladder, packed and bracketed.
%   BASECFG, optional, is merged into every rung beside the swept key: the write
%   source needs states_per_device set to mean anything. Empty is the original
%   behaviour, a config holding the swept key alone.
    if nargin < 7
        baseCfg = struct();
    end
    fprintf('  %-22s %d magnitudes x %d realizations\n', key, numel(mags), nReal);

    cfgs = cell(1, numel(mags));
    for i = 1:numel(mags)
        cfgs{i} = baseCfg;
        cfgs{i}.(key) = mags(i);
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
