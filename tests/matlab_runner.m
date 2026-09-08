function matlab_runner()
%MATLAB_RUNNER Exercise the inherited Monte Carlo harness; print one JSON object.
%   Driven by tests/test_matlab_harness.py. Reports facts and asserts nothing --
%   the assertions live in Python, where a failure names something and where the
%   whole suite is run from.
%
%   One invocation covers every MATLAB check in the suite because `matlab -batch`
%   costs about 27 seconds to start. Four per-test invocations would be two
%   minutes, and a suite that slow stops being run.
%
%   mc.sweep prints a progress line per magnitude, so the payload is delimited by
%   a marker rather than being assumed to own stdout.

    here = fileparts(mfilename('fullpath'));
    addpath(fullfile(here, '..', 'spinn-hw'));

    out = struct();
    out.validate = check_validate();
    out.sweep    = check_sweep_and_pack();
    out.detector = check_detector();

    fprintf('<<<JSON>>>\n%s\n', jsonencode(out));
end


function v = check_validate()
%CHECK_VALIDATE mc.validate_config must reject a key no driver reads.
%   The failure it guards is the worst available to this project: a misspelled
%   field selects nothing, the run completes cleanly at every magnitude, and the
%   flat curve reads as a tolerant design.
%
%   Uses arch "mesh" because that is one of the two the inherited registry knows.
%   A "crossbar" arch is plan 04's, and naming its keys early is exactly what that
%   plan argues against.

    v.goodAccepted = true;
    try
        mc.validate_config(struct('quant_bits', 8, 'phase_sigma_rad', 0.1), "mesh");
    catch e
        v.goodAccepted = false;
        v.goodError = e.message;
    end

    v.typoRejected = false;
    v.identifier = "";
    v.message = "";
    try
        mc.validate_config(struct('quant_bits', 8, 'phase_sigmaa', 0.1), "mesh");
    catch e
        v.typoRejected = true;
        v.identifier = string(e.identifier);
        v.message = string(e.message);
    end

    v.unknownArchRejected = false;
    try
        mc.error_sources("crossbar");
    catch e
        v.unknownArchRejected = true;
        v.archIdentifier = string(e.identifier);
    end
end


function s = check_sweep_and_pack()
%CHECK_SWEEP_AND_PACK The seed partitioning the whole comparison rests on.
%   mc.sweep's own comment says it was lifted out of the D2NN driver to stop two
%   drivers drifting apart on how a sweep is seeded, "which is the thing that
%   would quietly make their tolerance tables incomparable". Nothing checked it.
%
%   The stub records every seed it is handed. Passing mcFn explicitly is also the
%   only way this runs at all: sweep's default is @mc.run_montecarlo, which this
%   repo does not have -- the drivers stayed in photonn.

    seenSeeds = [];
    nMag = 4;
    nReal = 5;
    baseSeed = 7;
    cfgs = {struct('a', 1), struct('a', 2), struct('a', 3), struct('a', 4)};

    acc = mc.sweep(struct(), cfgs, nReal, baseSeed, @stub);

    s.seeds = seenSeeds;
    s.baseSeed = baseSeed;
    s.nMag = nMag;
    s.nReal = nReal;
    s.size = size(acc);
    s.acc = acc;

    mags = [0.1 0.2 0.3 0.4];
    packed = mc.pack(mags, acc, 0.5);
    s.packMagnitudes = packed.magnitudes;
    s.packAccMean = packed.accMean;
    s.packAccStd = packed.accStd;
    s.packThreshold = packed.threshold;
    s.packFields = string(fieldnames(packed))';

    function st = stub(~, cfg, n, seed)
        % Deterministic and distinguishable per config, so pack's statistics can
        % be recomputed independently in Python rather than trusted.
        seenSeeds(end+1) = seed; %#ok<AGROW>
        st.acc = cfg.a * 0.1 + (0:(n - 1)) * 0.01;
        st.mean = mean(st.acc);
    end
end


function d = check_detector()
%CHECK_DETECTOR err.detector_noise on a current vector rather than photon counts.
%   The open Tier 1 question. It is written against per-region photon counts; the
%   crossbar's counterpart is charge at a sense amplifier. Establish that it runs
%   and is dimensionally indifferent -- adapting it is plan 04's, not this plan's.
%
%   Its docstring points at docs/parameter_sources.md, which this repo lacks.

    currents = [1.0e-6 2.0e-6 5.0e-6 1.0e-5];
    opts = struct('read_noise_e', 1.0e-9, 'adc_bits', 8);

    a = err.detector_noise(currents, opts, 42);
    b = err.detector_noise(currents, opts, 42);
    c = err.detector_noise(currents, opts, 43);

    d.size = size(a);
    d.allFinite = all(isfinite(a));
    d.nonNegative = all(a >= 0);
    d.reproducible = isequal(a, b);
    d.seedChangesDraw = ~isequal(a, c);

    % With the ADC off and no read noise, only shot noise applies -- and at these
    % magnitudes sqrt(x) dwarfs x, so the guard against negatives is what keeps
    % the result physical. Recorded rather than asserted: it is a property of the
    % Gaussian approximation, not of this repo.
    quiet = err.detector_noise(currents, struct('read_noise_e', 0, 'adc_bits', 0), 42);
    d.quietNonNegative = all(quiet >= 0);
    d.quietSize = size(quiet);
end
