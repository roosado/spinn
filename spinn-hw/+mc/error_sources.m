function keys = error_sources(arch)
%ERROR_SOURCES Every errorConfig field a Monte Carlo driver recognises.
%   KEYS = MC.ERROR_SOURCES(ARCH) returns the recognised field names for ARCH,
%   which is "crossbar", "d2nn" or "mesh".
%
%   This list exists because "absent = source off" is the drivers' entire
%   selection mechanism, and an unrecognised field is indistinguishable from an
%   absent one. Write .phase_sigma instead of .phase_sigma_rad and the run
%   completes cleanly at every magnitude, produces a flat tolerance curve, and
%   supports the conclusion that the design is insensitive to phase error. For a
%   project whose deliverable is a tolerance document, that is the worst failure
%   available here, and it was one typo away with nothing to catch it -- the
%   valid key set existed only as a comment block, separately, in each driver.
%
%   Adding an error source means adding its key here. See MC.VALIDATE_CONFIG.

    arguments
        arch (1,1) string
    end

    shared = ["quant_bits", "delta_lambda_m", "phase_sigma_rad", "detector", "subset"];

    switch arch
        case "crossbar"
            % Named here, alongside the +err functions that read them, and not
            % earlier. These names are the config API: a recorded Monte Carlo
            % result is keyed to them, so renaming one afterwards invalidates
            % every run that used it. Naming them before the parameterisation
            % existed would have guaranteed at least one rename.
            %
            % Only sources 1-3, the comparable core. Sources 4-7 (sneak paths,
            % read noise, ADC quantisation, retention drift) get their keys when
            % they get their implementations, for the same reason.
            keys = [ ...
                ... % 1. err.conductance_variation -- stochastic, the likely binder.
                ... %    Relative to the window span, not in siemens: the reporting
                ... %    unit is log2(range/sigma), so bits = -log2(sigma_g_rel)
                ... %    directly, with no window in the conversion.
                "sigma_g_rel", ...
                ... % 2. err.quantize -- levels per *device*. Under a differential
                ... %    pair the effective weight resolves finer than this.
                "states_per_device", ...
                ... % 3. err.ir_drop -- ohms per wire segment between adjacent
                ... %    cells. Deterministic, position-dependent, and it grows
                ... %    with array size, so the size belongs beside any number
                ... %    derived from it.
                "wire_resistance_ohm", ...
                ... % shared: test-set subsetting, for speed only.
                "subset"];
        case "d2nn"
            keys = [shared, ...
                ... % device: what is wrong inside the parts
                "crosstalk_kernel", "loss_insertion_db", "loss_propagation_db_per_cm", ...
                ... % geometry: where the parts sit
                "spacing_sigma_m", "registration_sigma_px", "phase_gain", ...
                "detector_sigma_px"];
        case "mesh"
            keys = [shared, ...
                "phase_fields", "coupler_dispersion_per_nm", "crosstalk_coupling", ...
                "coupler_epsilon", "mzi_loss_db", "propagation_db_per_cm", "mzi_pitch_cm"];
        otherwise
            error("mc:error_sources:badArch", ...
                "Unknown architecture '%s'; expected 'crossbar', 'd2nn' or 'mesh'.", arch);
    end
end
