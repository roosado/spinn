function stats = run_montecarlo_crossbar(handoff, errorConfig, nRealizations, baseSeed)
%RUN_MONTECARLO_CROSSBAR Drive Monte Carlo realizations of the as-built crossbar.
%   STATS = MC.RUN_MONTECARLO_CROSSBAR(HANDOFF, ERRORCONFIG, NREALIZATIONS, BASESEED)
%   applies the configured +err perturbations to the ideal array in HANDOFF over
%   NREALIZATIONS draws, evaluates accuracy on the frozen test set (via
%   model.crossbar), and returns summary statistics.
%
%   This satisfies the contract mc.sweep requires -- (handoff, errorConfig,
%   nRealizations, baseSeed) returning a struct with .acc and .mean -- and it has
%   to be passed to mc.sweep **explicitly**. sweep's own default is
%   @mc.run_montecarlo, which this repo does not have: photonn kept its drivers
%   and spinn took only the shared harness. Leaving sweep.m byte-identical is
%   worth more than the convenience, because its seed partitioning is what keeps
%   the two platforms' tolerance tables comparable.
%
%   ERRORCONFIG selects which sources are active (all fields optional; absent =
%   source off):
%     .sigma_g_rel        - err.conductance_variation (stochastic), sigma as a
%                           fraction of the conductance span
%     .states_per_device  - err.quantize (deterministic), levels per device
%     .wire_resistance_ohm- err.ir_drop (deterministic), ohms per wire segment
%     .subset             - test-set indices (speed)
%
%   Deterministic sources are identical across realizations; the Monte Carlo
%   spread comes from the stochastic ones. With only source 1 stochastic, a
%   configuration carrying just sources 2 and 3 gives zero variance across
%   realizations -- that is correct, not a bug, and mc.pack will report a
%   standard deviation of exactly zero.
%
%   Each stochastic source draws from its own offset of SEED rather than sharing
%   one stream, so adding a source to a joint configuration cannot change the draw
%   another source gets. Without that a joint run is not the sum of the
%   independent ones it is supposed to be compared against. One source is
%   stochastic today; the offsets are laid out now so sources 4-7 slot in without
%   disturbing any recorded run.

    % Every source is selected by field presence, so a misspelled field is a
    % source that silently never runs and a tolerance curve that is flat because
    % nothing was perturbed. Checked once, here, before any realization is drawn.
    mc.validate_config(errorConfig, "crossbar");

    SEED_CONDUCTANCE = 0;      % offsets reserved in units of 10000; see above

    subset = [];
    if isfield(errorConfig, 'subset'), subset = errorConfig.subset; end

    % Deterministic, and outside the loop because they do not vary by realization.
    %
    % Quantisation happens *at* programming rather than after it: choosing which
    % device states represent a weight is part of programming. It also has to come
    % before the variation draw -- a device is set to one of the states it has, and
    % *then* its actual conductance deviates from that target. The other order
    % would quantise the error away.
    states = [];
    if isfield(errorConfig, 'states_per_device')
        states = errorConfig.states_per_device;
    end
    baseG = model.program(handoff, handoff.parameters.weights, states);

    Rwire = 0;
    if isfield(errorConfig, 'wire_resistance_ohm')
        Rwire = errorConfig.wire_resistance_ohm;
    end

    images = handoff.test_set.images;
    if ~isempty(subset), images = images(:, :, subset); end
    V = model.encode(handoff, images);

    acc = zeros(nRealizations, 1);
    seeds = zeros(nRealizations, 1);

    for i = 1:nRealizations
        seed = baseSeed + i - 1;
        seeds(i) = seed;

        G = baseG;
        if isfield(errorConfig, 'sigma_g_rel')
            G = err.conductance_variation(G, errorConfig.sigma_g_rel, handoff, ...
                                          seed + SEED_CONDUCTANCE);
        end

        opts = struct('conductances', G, 'voltages', V, 'subset', subset);
        if Rwire > 0
            opts.currents = err.ir_drop(V, G, Rwire, handoff);
        end

        out = model.crossbar(handoff, opts);
        acc(i) = out.accuracy;
    end

    stats.acc = acc;
    stats.mean = mean(acc);
    stats.std = std(acc);
    stats.seeds = seeds;
    stats.baseSeed = baseSeed;
end
