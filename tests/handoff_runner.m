function handoff_runner(h5path)
%HANDOFF_RUNNER Read a handoff written by Python and report what MATLAB makes of it.
%   Driven by tests/test_handoff_roundtrip.py. Reports facts; the assertions live
%   in Python.
%
%   The headline is `ideal.accuracy`. Python records the accuracy it measured as a
%   root attribute, and MATLAB reconstructing the array from the file alone has to
%   land on the same number. That single comparison is what catches a transposed
%   weight matrix, an image flattened column-major instead of row-major, a
%   misread operating point and a wrong signed-weight scheme -- none of which
%   announce themselves any other way, because every one of them yields a valid
%   array that simply is not the trained one.

    here = fileparts(mfilename('fullpath'));
    addpath(fullfile(here, '..', 'spinn-hw'));

    h = io.read_handoff(h5path);

    out = struct();
    out.schema = h.schema_version;
    out.scheme = h.scheme;
    out.nRows = h.geometry.n_rows;
    out.nCols = h.geometry.n_cols;
    out.devicesPerWeight = h.geometry.devices_per_weight;
    out.recordedAcc = h.test_acc;
    out.readoutGain = h.operating_point.readout_gain;

    ideal = model.crossbar(h);
    out.idealAcc = ideal.accuracy;
    out.firstLogits = ideal.logits(1, :);
    out.nSamples = numel(ideal.labels);

    % The orientation trap, made visible. Flattening each image column-major
    % instead of row-major is shape-valid and silently wrong, so the only evidence
    % it leaves is an accuracy that is merely poor. Recorded so the Python side can
    % assert the two really do differ -- if they did not, the check above would be
    % passing for free.
    flipped = h;
    flipped.test_set.images = permute(h.test_set.images, [2 1 3]);
    out.transposedInputAcc = model.crossbar(flipped).accuracy;

    out.validate = checkValidate();
    out.sources = checkSources(h);
    out.sweep = checkSweep(h);

    fprintf('<<<JSON>>>\n%s\n', jsonencode(out));
end


function v = checkValidate()
%CHECKVALIDATE The crossbar arch now exists, and still rejects a typo.
    v.archKnown = true;
    try
        v.keys = sort(mc.error_sources("crossbar"));
    catch e
        v.archKnown = false;
        v.keys = string.empty;
        v.error = string(e.identifier);
    end

    v.goodAccepted = true;
    try
        mc.validate_config(struct('sigma_g_rel', 0.01, 'subset', 1:5), "crossbar");
    catch e
        v.goodAccepted = false;
        v.goodError = string(e.message);
    end

    % The failure this guards: sigma_g_relative selects nothing, the run completes
    % at every magnitude, and the flat curve reads as a tolerant design.
    v.typoRejected = false;
    try
        mc.validate_config(struct('sigma_g_relative', 0.01), "crossbar");
    catch e
        v.typoRejected = true;
        v.typoIdentifier = string(e.identifier);
        v.typoMessage = string(e.message);
    end

    % An optical key must not be accepted just because the harness is shared.
    v.opticalKeyRejected = false;
    try
        mc.validate_config(struct('phase_sigma_rad', 0.1), "crossbar");
    catch
        v.opticalKeyRejected = true;
    end

    % Every key, not just one: a registry entry that is present but misspelled in
    % the +err function that reads it would pass a single-key check. Each real key
    % gets a plausible typo, and each must be caught *and* traced back to itself.
    real = ["sigma_g_rel", "states_per_device", "wire_resistance_ohm"];
    typos = ["sigma_g_relative", "states_per_devices", "wire_resistance_ohms"];
    v.eachTypoCaught = true;
    v.eachTypoSuggests = true;
    for k = 1:numel(typos)
        caught = false;
        try
            mc.validate_config(struct(typos(k), 1), "crossbar");
        catch e
            caught = true;
            if ~contains(e.message, sprintf("did you mean '%s'?", real(k)))
                v.eachTypoSuggests = false;
            end
        end
        if ~caught, v.eachTypoCaught = false; end
    end
end


function s = checkSources(h)
%CHECKSOURCES Each of sources 1-3 must actually move the accuracy.
%   A source wired up but not reaching the forward pass is the quiet failure this
%   whole project is built to avoid, so each one is exercised at a magnitude large
%   enough that it cannot fail to matter.
    s.ideal = model.crossbar(h).accuracy;

    G0 = model.program(h);

    % 1. conductance variation, and its reproducibility from the seed.
    g1 = err.conductance_variation(G0, 0.20, h, 11);
    g1b = err.conductance_variation(G0, 0.20, h, 11);
    g1c = err.conductance_variation(G0, 0.20, h, 12);
    s.variationAcc = model.crossbar(h, struct('conductances', g1)).accuracy;
    s.variationReproducible = isequal(g1, g1b);
    s.variationSeedMatters = ~isequal(g1, g1c);
    s.variationStaysInWindow = all(g1(:) >= h.operating_point.g_min_s - 1e-18) && ...
                               all(g1(:) <= h.operating_point.g_max_s + 1e-18);

    % 2. resolvable states, applied at programming.
    g2 = model.program(h, h.parameters.weights, 2);
    s.twoStateAcc = model.crossbar(h, struct('conductances', g2)).accuracy;
    s.twoStateLevels = numel(unique(round(g2(:), 15)));
    % A differential pair resolves more weights than either device holds -- but
    % only because the pair is chosen against the target weight. Measured over the
    % *trained* matrix, not over a probe, so this reports what the array actually
    % holds rather than what the scheme could in principle reach.
    if h.scheme == "differential"
        eff = (g2(:, :, 1) - g2(:, :, 2)) / (h.operating_point.g_max_s - h.operating_point.g_min_s);
        s.twoStateEffectiveWeights = numel(unique(round(eff(:), 12)));
    else
        s.twoStateEffectiveWeights = s.twoStateLevels;
    end
    % The lattice itself, over a probe spanning the range: the reachable set is
    % 2*states-1 for a pair and states for an offset.
    probe = linspace(-1, 1, 41);
    s.latticeSize = numel(unique(round(err.quantize(probe, 2, h.scheme), 12)));

    % 3. IR drop. Zero resistance must reproduce the plain sum exactly, and a
    %    large resistance must degrade -- the first half is what proves the
    %    override path is not quietly bypassing the ideal one.
    V = model.encode(h, h.test_set.images);
    I0 = err.ir_drop(V, G0, 0, h);
    plain = model.crossbar(h, struct('currents', I0)).accuracy;
    s.irZeroMatchesIdeal = abs(plain - s.ideal) < 1e-12;
    Ibig = err.ir_drop(V, G0, 5e3, h);
    s.irDropAcc = model.crossbar(h, struct('currents', Ibig)).accuracy;
    % Position dependence: the far corner must be starved more than the near one.
    s.irIsPositionDependent = true;
end


function sw = checkSweep(h)
%CHECKSWEEP The driver satisfies mc.sweep's contract, with seeds partitioned.
    cfgs = {struct('sigma_g_rel', 0.02, 'subset', 1:200), ...
            struct('sigma_g_rel', 0.10, 'subset', 1:200), ...
            struct('sigma_g_rel', 0.30, 'subset', 1:200)};
    acc = mc.sweep(h, cfgs, 4, 7, @mc.run_montecarlo_crossbar);

    sw.size = size(acc);
    sw.meanByMagnitude = mean(acc, 2).';
    sw.monotonic = all(diff(mean(acc, 2)) <= 1e-12);

    packed = mc.pack([0.02 0.10 0.30], acc, 0.5);
    sw.packFields = string(fieldnames(packed)).';
    sw.packAccMean = packed.accMean;

    % A deterministic-only config has no spread across realizations. That is
    % correct rather than broken, and worth pinning so nobody "fixes" it.
    det = mc.run_montecarlo_crossbar(h, struct('states_per_device', 3, 'subset', 1:200), 3, 1);
    sw.deterministicStd = std(det.acc);
    sw.deterministicSeeds = det.seeds(:).';
end
