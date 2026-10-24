-- Background worker jobs (file based; no network, no blocking).

return function(util, json)
	local W = {}

	W.STALL_TIMEOUT = 180 -- seconds without any status change => failure

	function W.engine_ready()
		local p = util.paths()
		if not util.exists(p.python) then
			return false, "The MaxTrace+ Python engine is not installed (" .. p.python .. "). Run install.sh again."
		end
		if not util.exists(p.worker) then
			return false, "MaxTrace+ engine files are missing (" .. p.worker .. "). Run install.sh again."
		end
		return true
	end

	function W.new(kind, spec)
		local p = util.paths()
		local id = os.date("%Y%m%d-%H%M%S") .. "-" .. util.uuid():sub(1, 6)
		local dir = util.join(p.jobs, id)
		if not util.mkdirs(dir) then
			return nil, "Cannot create the job folder " .. dir
		end
		spec.job = kind
		spec.cache_dir = spec.cache_dir or p.cache
		spec.log_dir = spec.log_dir or p.logs
		local ok, txt = pcall(json.encode, spec, true)
		if not ok then
			return nil, "Could not encode job: " .. tostring(txt)
		end
		local wok, werr = util.write(util.join(dir, "job.json"), txt)
		if not wok then
			return nil, "Could not write job file: " .. tostring(werr)
		end
		return { id = id, dir = dir, kind = kind, spec = spec }
	end

	function W.start(job)
		local ready, why = W.engine_ready()
		if not ready then
			return false, why
		end
		local p = util.paths()
		util.mkdirs(p.logs)
		local inner = string.format(
			"%s -I %s %s >> %s 2>&1 &",
			util.shq(p.python),
			util.shq(p.worker),
			util.shq(job.dir),
			util.shq(util.join(p.logs, "worker-stdout.log"))
		)
		local ok = util.exec("/bin/sh -c " .. util.shq(inner))
		if not ok then
			return false, "Could not start the MaxTrace+ engine process."
		end
		job.started = os.time()
		job.last_change = os.time()
		job.last_token = nil
		util.info("job %s (%s) started", job.id, job.kind)
		return true
	end

	-- Returns: state ("running" | "done" | "failed"), payload
	function W.poll(job)
		local rpath = util.join(job.dir, "result.lua")
		if util.exists(rpath) then
			local res, err = util.load_table(rpath)
			if not res then
				return "failed", { ok = false, code = "bad_result", message = "Unreadable engine result: " .. tostring(err) }
			end
			return "done", res
		end
		local st = util.load_table(util.join(job.dir, "status.lua"))
		local token = st and (tostring(st.time) .. tostring(st.progress)) or nil
		if token and token ~= job.last_token then
			job.last_token = token
			job.last_change = os.time()
		end
		if os.time() - (job.last_change or os.time()) > W.STALL_TIMEOUT then
			return "failed", { ok = false, code = "stalled", message = "The MaxTrace+ engine stopped responding. See the log for details." }
		end
		return "running", st
	end

	function W.cancel(job)
		if job and job.dir then
			util.write(util.join(job.dir, "cancel"), "1")
		end
	end

	return W
end
