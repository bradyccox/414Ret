local unitPayloads = {
	["name"] = "F-14A",
	["payloads"] = {
		[1] = {
			["name"] = "CAP",
			["pylons"] = {
				[1] = {
					["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}",
					["num"] = 1,
				},
				[2] = {
					["CLSID"] = "{8D399DDA-FF81-4F14-904D-099B34FE7918}",
					["num"] = 2,
				},
				[3] = {
					["CLSID"] = "{7575BA0B-7294-4844-857B-031A144B2595}",
					["num"] = 4,
				},
				[4] = {
					["CLSID"] = "{7575BA0B-7294-4844-857B-031A144B2595}",
					["num"] = 9,
				},
				[5] = {
					["CLSID"] = "{8D399DDA-FF81-4F14-904D-099B34FE7918}",
					["num"] = 11,
				},
				[6] = {
					["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}",
					["num"] = 12,
				},
				[7] = {
					["CLSID"] = "{82364E69-5564-4043-A866-E13032926C3E}",
					["num"] = 10,
				},
				[8] = {
					["CLSID"] = "{82364E69-5564-4043-A866-E13032926C3E}",
					["num"] = 3,
				},
				[9] = {
					["CLSID"] = "{8D399DDA-FF81-4F14-904D-099B34FE7918}",
					["num"] = 7,
				},
			},
			["tasks"] = {
				[1] = 10,
			},
		},
		[2] = {
			-- TARPS recon profile for the AI F-14A. The real F-14A was the US
			-- Navy's TARPS platform, so it carries the {F14-TARPS} camera pod on
			-- the belly plus a light self-defense fit (2x AIM-9, 2x AIM-7, drop
			-- tanks). NOTE: this AI airframe is a separate DCS unit from the
			-- flyable Tomcats; the pod station here is NOT editor-verified the
			-- way the F-14B build is -- confirm it renders in the ME.
			["displayName"] = "Retribution TARPS",
			["name"] = "Retribution TARPS",
			["pylons"] = {
				[1] = {
					["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}",
					["num"] = 1,
				},
				[2] = {
					["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}",
					["num"] = 12,
				},
				[3] = {
					["CLSID"] = "{8D399DDA-FF81-4F14-904D-099B34FE7918}",
					["num"] = 2,
				},
				[4] = {
					["CLSID"] = "{8D399DDA-FF81-4F14-904D-099B34FE7918}",
					["num"] = 11,
				},
				[5] = {
					["CLSID"] = "{82364E69-5564-4043-A866-E13032926C3E}",
					["num"] = 3,
				},
				[6] = {
					["CLSID"] = "{82364E69-5564-4043-A866-E13032926C3E}",
					["num"] = 10,
				},
				[7] = {
					["CLSID"] = "{F14-TARPS}",
					["num"] = 6,
				},
			},
			["tasks"] = {
				[1] = 10,
			},
		},
	},
	["unitType"] = "F-14A",
}
return unitPayloads
