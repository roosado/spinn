function handoff_runner(h5path, recordedPath)
%HANDOFF_RUNNER Read a handoff written by Python and report what MATLAB makes of it.
%   Driven by tests/test_handoff_roundtrip.py. Reports facts; the assertions live
%   in Python.
%
%   RECORDEDPATH, optional, is the trained array the published row was measured on
%   (exports/crossbar_handoff.h5, which is gitignored). When it exists the IR-drop
%   numbers the row records are recomputed from it, so a change to err.ir_drop has to
%   reproduce them rather than merely agree with itself.
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
    out.irDrop = checkIrDrop(h);
    if nargin >= 2 && isfile(recordedPath)
        out.recordedIr = recordedIr(recordedPath);
    end

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

    % The property the per-source seed offsets exist for, tested directly rather
    % than inferred from a joint run being the sum of the independents -- which it
    % is not, because accuracy saturates.
    %
    % What must hold is that adding a source cannot change the draw another source
    % gets. Here: the same seed must produce the same *perturbation*, whatever base
    % conductances it is applied to. If it did not, a joint configuration would be
    % comparing against draws the independent runs never saw.
    G0 = model.program(h);
    G2 = model.program(h, h.parameters.weights, 4);   % a different base
    n1 = err.conductance_variation(G0, 0.05, h, 42) - G0;
    n2 = err.conductance_variation(G2, 0.05, h, 42) - G2;
    % Clamping at the window edge makes the two differ where a base sits against an
    % edge, so compare only where neither is clamped -- the draw itself.
    gmin = h.operating_point.g_min_s; gmax = h.operating_point.g_max_s;
    free = (G0 > gmin) & (G0 < gmax) & (G2 > gmin) & (G2 < gmax) & ...
           (abs(n1) < (gmax - gmin) * 0.5) & (abs(n2) < (gmax - gmin) * 0.5);
    sw.drawIndependentOfBase = max(abs(n1(free) - n2(free))) < 1e-18;
    sw.drawComparedCount = sum(free(:));
end


function s = checkIrDrop(h)
%CHECKIRDROP The wire network against cases that can be worked by hand, and the
%   blocking and iteration added to err.ir_drop for the array-size sweep.

    % 1. A uniform array, first order, in closed form.
    %    Every cell G, every row driven at v: the segment before column j carries
    %    (M-k+1) cells' worth of current for k = 1..j, and likewise down the column,
    %        Veff(i,j) = v - R v G (rowDrop(j) + colDrop(i)),
    %    with rowDrop(j) = j(2M-j+1)/2 and colDrop(i) = i(2N-i+1)/2. The far corner
    %    (N, M) loses R v G (N(N+1) + M(M+1))/2. The column current is G * sum_i Veff.
    N = 5; M = 3; g = 2e-6; v = 0.1; R = 1e3;
    I = err.ir_drop(v * ones(1, N), g * ones(N, M), R, h);
    j = 1:M; i = (1:N).';
    rowDrop = j .* (2 * M - j + 1) / 2;
    colDrop = i .* (2 * N - i + 1) / 2;
    expected = g * (N * v - R * v * g * (N * rowDrop + sum(colDrop)));
    s.uniformMaxRelErr = max(abs(I - expected) ./ expected);
    s.uniformDropFraction = R * g * (N * (N + 1) + M * (M + 1)) / 2;

    % 2. One cell, where the exact network is a series resistance:
    %    I = v g / (1 + 2 R g) exactly, against v g (1 - 2 R g) at first order.
    v1 = 0.1; g1 = 2e-6; R1 = 1e5;
    s.oneCell.v = v1; s.oneCell.g = g1; s.oneCell.r = R1;
    s.oneCell.first = err.ir_drop(v1, g1, R1, h);
    s.oneCell.exact = err.ir_drop_exact(v1, g1, R1, h);

    % 3. The exact solve against a direct nodal solve written out node by node in
    %    this file, which shares no code with it. A 4-by-3 array with a large drop,
    %    so the two are not agreeing on a case where the correction is negligible.
    stream = RandStream('mt19937ar', 'Seed', 3);
    Ns = 4; Ms = 3; Rs = 2e4;
    Gs = 1e-6 + 2e-6 * rand(stream, Ns, Ms);
    Vs = 0.1 * rand(stream, 3, Ns);
    Iref = nodalSolve(Vs, Gs, Rs);
    Iexact = err.ir_drop_exact(Vs, Gs, Rs, h);
    Iideal = err.ir_drop(Vs, Gs, 0, h);
    Ifirst = err.ir_drop(Vs, Gs, Rs, h);
    s.nodalMaxRelErr = max(abs(Iexact(:) - Iref(:)) ./ abs(Iref(:)));
    s.nodalCurrentLostFraction = max(1 - Iref(:) ./ Iideal(:));
    % First order overstates the drop, so it sits below the network's answer, which
    % sits below the ideal. Elementwise, because V and G are non-negative.
    s.firstOrderBelowNetworkBelowIdeal = all(Ifirst(:) <= Iref(:)) && all(Iref(:) <= Iideal(:));

    % 4. Accuracy under IR drop depends on R*G alone. Scale every conductance by
    %    alpha and every wire resistance by 1/alpha and each drop, and so each
    %    argmax, is unchanged. With alpha a power of two the scaling is exact, so
    %    the currents must be identical; alpha = 3 is the same claim to rounding.
    V = model.encode(h, h.test_set.images);
    G0 = model.program(h);
    Rw = 1e3;
    base = err.ir_drop(V, G0, Rw, h);
    baseExact = err.ir_drop_exact(V, G0, Rw, h);
    s.accIdeal = model.crossbar(h).accuracy;
    s.accWithDrop = model.crossbar(h, struct('currents', base)).accuracy;
    for alpha = [4 3]
        h2 = h;
        h2.operating_point.g_min_s = alpha * h.operating_point.g_min_s;
        h2.operating_point.g_max_s = alpha * h.operating_point.g_max_s;
        G2 = model.program(h2);
        I2 = err.ir_drop(V, G2, Rw / alpha, h2);
        acc2 = model.crossbar(h2, struct('currents', I2)).accuracy;
        key = sprintf('alpha%d', alpha);
        s.scaling.(key).currentsIdentical = isequal(I2, alpha * base);
        % Against the largest current, not elementwise: at this resistance the drop
        % rivals the drive, so Veff is a difference of nearly equal numbers and an
        % individual small current carries rounding the large ones do not.
        s.scaling.(key).maxScaledErr = max(abs(I2(:) - alpha * base(:))) / max(abs(alpha * base(:)));
        s.scaling.(key).acc = acc2;
        % The exact network is a function of R*G too: its nodal matrix is the wires
        % plus R*G, and Geff is read out as a conductance, so it scales with alpha.
        Iex2 = err.ir_drop_exact(V, G2, Rw / alpha, h2);
        s.scaling.(key).exactMaxScaledErr = ...
            max(abs(Iex2(:) - alpha * baseExact(:))) / max(abs(alpha * baseExact(:)));
    end

    % 5. Blocks are invisible. The reference is err.ir_drop as it was before it was
    %    blocked, kept here on purpose: it is what "bit-identical" is measured against.
    Vpart = V(1:1234, :);                    % four full blocks and a partial one
    s.blockedEqualsUnblockedTrained = isequal( ...
        err.ir_drop(Vpart, G0, 300, h), referenceIrDrop(Vpart, G0, 300));
    stream = RandStream('mt19937ar', 'Seed', 5);
    Gb = 1e-6 + 2e-6 * rand(stream, 676, 10, 2);     % the largest size the sweep reaches
    Vb = 0.1 * rand(stream, 600, 676);
    s.blockedEqualsUnblockedLarge = isequal( ...
        err.ir_drop(Vb, Gb, 2, h), referenceIrDrop(Vb, Gb, 2));

    % 6. err.ir_drop is the first-order expansion of the exact network, so at a
    %    resistance small enough that the second-order term is negligible the two must
    %    lose the same current. This is what ties the first-order geometry -- where the
    %    drivers and the amplifiers sit -- to the network's, on a trained array rather
    %    than a toy one. The exact solve at zero resistance must be the ideal sum.
    Rsmall = 0.1;
    I0 = err.ir_drop(V, G0, 0, h);
    I1 = err.ir_drop(V, G0, Rsmall, h);
    Ix = err.ir_drop_exact(V, G0, Rsmall, h);
    s.geometryLossRatio = sum(I0(:) - I1(:)) / sum(I0(:) - Ix(:));
    s.exactAtZeroIsIdeal = isequal(err.ir_drop_exact(V, G0, 0, h), I0);

    % 7. The exact model cannot do what first order does past its range: lift a
    %    column node above the driver that feeds it. Every cell current stays
    %    non-negative for non-negative drives, however large the wire resistance.
    Ihuge = err.ir_drop_exact(V, G0, 1e5, h);
    s.exactCurrentsNonNegativeAtHugeR = all(Ihuge(:) >= -1e-12 * max(Ihuge(:)));
    s.firstOrderGoesNegativeAtHugeR = any(reshape(err.ir_drop(V, G0, 1e5, h), [], 1) < 0);
end


function r = recordedIr(path)
%RECORDEDIR The row's own array at the two wire resistances it records.
    hr = io.read_handoff(path);
    V = model.encode(hr, hr.test_set.images);
    G = model.program(hr);
    r.ideal = model.crossbar(hr).accuracy;
    for R = [100 300]
        acc = model.crossbar(hr, struct('currents', err.ir_drop(V, G, R, hr))).accuracy;
        r.(sprintf('acc%d', R)) = acc;
    end
end


function I = nodalSolve(V, G, R)
%NODALSOLVE The resistive network by a direct linear solve: the oracle.
%   Unknowns are the voltage at every row-wire node and every column-wire node.
%   Row drivers sit at the column-1 edge and the amplifier at the row-1 edge,
%   holding its wire at ground, as in err.ir_drop. Kirchhoff's current law at each
%   node, solved with backslash; no cumulative sums and no iteration, so it shares
%   nothing with the function it checks.
    [N, M] = size(G);
    g = 1 / R;
    nn = N * M;
    rIdx = @(i, j) (j - 1) * N + i;
    cIdx = @(i, j) nn + (j - 1) * N + i;
    I = zeros(size(V, 1), M);
    for k = 1:size(V, 1)
        A = zeros(2 * nn);
        b = zeros(2 * nn, 1);
        for i = 1:N
            for j = 1:M
                r = rIdx(i, j);  c = cIdx(i, j);

                % Row node: the segment behind it (to the driver, or the node
                % before), the segment ahead if there is one, and the device.
                A(r, r) = A(r, r) + g + G(i, j);
                A(r, c) = A(r, c) - G(i, j);
                if j == 1
                    b(r) = b(r) + g * V(k, i);
                else
                    A(r, rIdx(i, j - 1)) = A(r, rIdx(i, j - 1)) - g;
                end
                if j < M
                    A(r, r) = A(r, r) + g;
                    A(r, rIdx(i, j + 1)) = A(r, rIdx(i, j + 1)) - g;
                end

                % Column node: the segment toward the amplifier (ground at i = 1),
                % the segment away if there is one, and the device.
                A(c, c) = A(c, c) + g + G(i, j);
                A(c, r) = A(c, r) - G(i, j);
                if i > 1
                    A(c, cIdx(i - 1, j)) = A(c, cIdx(i - 1, j)) - g;
                end
                if i < N
                    A(c, c) = A(c, c) + g;
                    A(c, cIdx(i + 1, j)) = A(c, cIdx(i + 1, j)) - g;
                end
            end
        end
        x = A \ b;
        for j = 1:M
            I(k, j) = g * x(cIdx(1, j));       % the current into the amplifier
        end
    end
end


function I = referenceIrDrop(V, G, Rwire)
%REFERENCEIRDROP err.ir_drop as it was before it was blocked, first order, whole batch.
%   Deliberately a copy: it is the thing the blocked version is required to equal.
    nDev = size(G, 3);
    I = zeros(size(V, 1), size(G, 2), nDev);
    Vd = permute(V, [2 3 1]);
    for d = 1:nDev
        Gd = G(:, :, d);
        I0 = Vd .* Gd;
        Irow = flip(cumsum(flip(I0, 2), 2), 2);
        dropRow = Rwire * cumsum(Irow, 2);
        Icol = flip(cumsum(flip(I0, 1), 1), 1);
        dropCol = Rwire * cumsum(Icol, 1);
        Veff = Vd - dropRow - dropCol;
        I(:, :, d) = permute(sum(Veff .* Gd, 1), [3 2 1]);
    end
end
