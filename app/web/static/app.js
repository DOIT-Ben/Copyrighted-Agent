    (() => {
      const feedback = document.getElementById("submit-feedback");
      const feedbackTitle = document.getElementById("submit-feedback-title");
      const feedbackDetail = document.getElementById("submit-feedback-detail");
      const feedbackProgressFill = document.getElementById("submit-feedback-progress-fill");
      const feedbackStep = document.getElementById("submit-feedback-step");
      const feedbackActions = document.getElementById("submit-feedback-actions");
      if (!feedback || !feedbackTitle || !feedbackDetail || !feedbackProgressFill || !feedbackStep || !feedbackActions) {
        return;
      }

      let stageTimer = null;
      const defaultSteps = ["文件已提交", "正在解析材料", "正在执行脱敏与审查", "正在整理结果页"];
      const wait = (milliseconds) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));
      const dimensionKeys = ["identity", "completeness", "consistency", "source_code", "software_doc", "agreement", "ai"];

      const stopStageTimer = () => {
        if (stageTimer !== null) {
          window.clearInterval(stageTimer);
          stageTimer = null;
        }
      };

      const runStageSequence = (steps, inlineStep) => {
        const activeSteps = steps.length ? steps : defaultSteps;
        let activeIndex = 0;

        const renderStep = () => {
          const progress = activeSteps.length <= 1 ? 100 : 18 + Math.round((activeIndex / (activeSteps.length - 1)) * 82);
          feedbackStep.textContent = activeSteps[activeIndex];
          feedbackProgressFill.style.width = progress + "%";
          if (inlineStep) {
            inlineStep.textContent = activeSteps.slice(0, activeIndex + 1).join(" -> ");
          }
        };

        stopStageTimer();
        renderStep();
        if (activeSteps.length <= 1) {
          return;
        }

        stageTimer = window.setInterval(() => {
          if (activeIndex >= activeSteps.length - 1) {
            stopStageTimer();
            return;
          }
          activeIndex += 1;
          renderStep();
        }, 1200);
      };

      const setFeedbackState = (state) => {
        feedback.classList.toggle("is-error", state === "error");
      };

      const clearFeedbackActions = () => {
        feedbackActions.innerHTML = "";
        feedbackActions.hidden = true;
      };

      const setFeedbackActions = (actions) => {
        if (!Array.isArray(actions) || !actions.length) {
          clearFeedbackActions();
          return;
        }
        feedbackActions.innerHTML = "";
        for (const item of actions) {
          if (!item || !item.label) {
            continue;
          }
          if (item.kind === "button") {
            const button = document.createElement("button");
            button.type = "button";
            button.className = item.primary ? "button-primary button-compact" : "button-secondary button-compact";
            button.textContent = String(item.label);
            button.addEventListener("click", () => item.onClick && item.onClick());
            feedbackActions.appendChild(button);
            continue;
          }
          const link = document.createElement("a");
          link.className = item.primary ? "button-primary button-compact" : "button-secondary button-compact";
          link.href = String(item.href || "#");
          link.textContent = String(item.label);
          feedbackActions.appendChild(link);
        }
        feedbackActions.hidden = feedbackActions.childElementCount === 0;
      };

      const jobFailureHint = (payload) => {
        const errorCode = String(payload.error_code || "").trim();
        const fallback = String(payload.error_message || payload.detail || "").trim();
        const hintMap = {
          worker_interrupted_during_runtime: "任务在处理过程中中断，可以重新发起导入。",
          filesystem_io_error: "文件读写阶段失败，稍后重试通常可以恢复。",
          source_file_missing: "原始上传文件已经不存在，建议重新上传 ZIP。",
          invalid_zip_archive: "ZIP 文件本身不可用，建议重新打包后再上传。",
          unsupported_submission_mode: "导入模式异常，请重新选择正确模式后提交。",
          unsupported_review_strategy: "审查策略异常，请刷新页面后重新提交。",
          invalid_submission_request: "这次提交参数不完整，建议返回首页重新提交。",
          unexpected_runtime_error: "系统处理过程中出现未预期错误，可以先重试一次。",
        };
        return hintMap[errorCode] || fallback || "处理失败，请稍后重试。";
      };

      const pollAsyncJob = async (statusUrl, redirectUrl, inlineStep, pendingDetail) => {
        for (;;) {
          const jobResponse = await window.fetch(statusUrl, { headers: { Accept: "application/json" } });
          if (!jobResponse.ok) {
            throw new Error(await readErrorMessage(jobResponse));
          }
          const jobPayload = await jobResponse.json();
          applyJobFeedback(jobPayload, inlineStep, pendingDetail);
          if (jobPayload.status === "completed") {
            clearFeedbackActions();
            feedbackTitle.textContent = "分析完成，正在跳转";
            feedbackDetail.textContent = jobPayload.detail || "批次结果已生成，即将进入详情页。";
            feedbackStep.textContent = jobPayload.stage || "结果已生成";
            feedbackProgressFill.style.width = "100%";
            if (inlineStep) {
              inlineStep.textContent = jobPayload.stage || "结果已生成";
            }
            window.setTimeout(() => {
              window.location.href = redirectUrl;
            }, 380);
            return;
          }
          if (jobPayload.status === "failed" || jobPayload.status === "interrupted") {
            const hint = jobFailureHint(jobPayload);
            throw Object.assign(new Error(hint), { jobPayload, redirectUrl });
          }
          await wait(900);
        }
      };

      const restoreForm = (form) => {
        form.dataset.submitting = "false";
        form.classList.remove("is-submitting");
        const submitButtons = Array.from(form.querySelectorAll('button[type="submit"], input[type="submit"]'));
        for (const button of submitButtons) {
          button.disabled = false;
          button.classList.remove("is-loading");
          if (button.tagName === "BUTTON" && button.dataset.originalHtml) {
            button.innerHTML = button.dataset.originalHtml;
          }
        }
      };

      const applyJobFeedback = (payload, inlineStep, fallbackDetail) => {
        const jobStage = String(payload.stage || "").trim();
        const jobDetail = String(payload.detail || "").trim();
        const jobProgress = Number(payload.progress || 0);
        feedbackStep.textContent = jobStage || defaultSteps[defaultSteps.length - 1];
        feedbackDetail.textContent = jobDetail || fallbackDetail;
        feedbackProgressFill.style.width = Math.max(8, Math.min(100, jobProgress || 8)) + "%";
        if (inlineStep) {
          inlineStep.textContent = jobStage || jobDetail || fallbackDetail;
        }
      };

      const readErrorMessage = async (response) => {
        try {
          const payload = await response.json();
          return payload.detail || payload.message || "提交失败，请稍后重试。";
        } catch (_error) {
          return "提交失败，请稍后重试。";
        }
      };

      const applyReviewPreset = (button) => {
        const form = button.closest("form");
        if (!form) {
          return;
        }
        const presetKey = String(button.dataset.reviewPreset || "").trim();
        const hiddenPreset = form.querySelector('input[name="review_profile_preset"]');
        if (hiddenPreset) {
          hiddenPreset.value = presetKey;
        }
        let profile = null;
        try {
          profile = JSON.parse(String(button.dataset.reviewProfile || "{}"));
        } catch (_error) {
          profile = null;
        }
        if (!profile) {
          return;
        }

        const focusMode = form.querySelector('select[name="focus_mode"]');
        const strictness = form.querySelector('select[name="strictness"]');
        const llmInstruction = form.querySelector('textarea[name="llm_instruction"]');
        if (focusMode && profile.focus_mode) {
          focusMode.value = profile.focus_mode;
        }
        if (strictness && profile.strictness) {
          strictness.value = profile.strictness;
        }
        if (llmInstruction) {
          llmInstruction.value = String(profile.llm_instruction || "");
        }
        const enabledDimensions = new Set(Array.isArray(profile.enabled_dimensions) ? profile.enabled_dimensions : []);
        for (const key of dimensionKeys) {
          const checkbox = form.querySelector('input[name="dimension_' + key + '"]');
          if (checkbox) {
            checkbox.checked = enabledDimensions.has(key);
          }
        }
        const siblingButtons = Array.from(form.querySelectorAll("[data-review-preset]"));
        for (const item of siblingButtons) {
          item.classList.toggle("is-active", item === button);
        }
      };

      const presetButtons = Array.from(document.querySelectorAll("[data-review-preset]"));
      for (const button of presetButtons) {
        button.addEventListener("click", () => applyReviewPreset(button));
      }

      const forms = Array.from(document.querySelectorAll("form[data-pending-text]"));
      for (const form of forms) {
        form.addEventListener("submit", async (event) => {
          if (form.dataset.submitting === "true") {
            event.preventDefault();
            return;
          }

          if (typeof form.reportValidity === "function" && !form.reportValidity()) {
            return;
          }

          form.dataset.submitting = "true";
          form.classList.add("is-submitting");
          document.body.classList.add("has-submit-feedback");

          const pendingText = form.dataset.pendingText || "正在处理，请稍候";
          const pendingDetail = form.dataset.pendingDetail || "系统正在提交你的请求。";
          const steps = (form.dataset.pendingSteps || "")
            .split("|")
            .map((item) => item.trim())
            .filter(Boolean);
          const inlineNote = form.querySelector("[data-inline-pending]");
          const inlineStep = form.querySelector("[data-inline-step]");
          if (inlineNote) {
            inlineNote.classList.remove("is-error");
            inlineNote.hidden = false;
          }
          clearFeedbackActions();
          feedbackTitle.textContent = pendingText;
          feedbackDetail.textContent = pendingDetail;
          feedback.hidden = false;
          setFeedbackState("running");
          runStageSequence(steps, inlineStep);

          const submitButtons = Array.from(form.querySelectorAll('button[type="submit"], input[type="submit"]'));
          for (const button of submitButtons) {
            button.disabled = true;
            button.classList.add("is-loading");
            if (button.tagName === "BUTTON") {
              if (!button.dataset.originalHtml) {
                button.dataset.originalHtml = button.innerHTML;
              }
              const pendingLabel = button.dataset.pendingLabel || pendingText;
              button.innerHTML = '<span class="button-spinner" aria-hidden="true"></span><span>' + pendingLabel + "</span>";
            }
          }

          const asyncUrl = form.dataset.asyncUploadUrl;
          if (!asyncUrl || !window.fetch || !window.FormData) {
            return;
          }

          event.preventDefault();
          try {
            const submitResponse = await window.fetch(asyncUrl, {
              method: (form.method || "POST").toUpperCase(),
              body: new window.FormData(form),
              headers: { Accept: "application/json" },
            });
            if (!submitResponse.ok) {
              throw new Error(await readErrorMessage(submitResponse));
            }

            const submitPayload = await submitResponse.json();
            const statusUrl = submitPayload.status_url || (submitPayload.job_id ? "/api/jobs/" + submitPayload.job_id : "");
            const redirectUrl = submitPayload.redirect_url || (submitPayload.submission_id ? "/submissions/" + submitPayload.submission_id : "/submissions");
            stopStageTimer();

            if (!statusUrl) {
              window.location.href = redirectUrl;
              return;
            }

            await pollAsyncJob(statusUrl, redirectUrl, inlineStep, pendingDetail);
          } catch (error) {
            stopStageTimer();
            setFeedbackState("error");
            feedbackTitle.textContent = "分析失败，请重试";
            const jobPayload = error && typeof error === "object" && "jobPayload" in error ? error.jobPayload : null;
            const redirectUrl = error && typeof error === "object" && "redirectUrl" in error ? error.redirectUrl : "";
            feedbackDetail.textContent = error instanceof Error ? error.message : "系统处理失败，请稍后重试。";
            feedbackStep.textContent = "本次提交未完成";
            feedbackProgressFill.style.width = "100%";
            if (inlineNote) {
              inlineNote.classList.add("is-error");
            }
            if (inlineStep) {
              inlineStep.textContent = error instanceof Error ? error.message : "系统处理失败，请稍后重试。";
            }
            const actions = [];
            if (redirectUrl) {
              actions.push({ kind: "link", label: "查看批次详情", href: redirectUrl, primary: false });
            }
            if (jobPayload && jobPayload.can_retry && jobPayload.retry_url) {
              actions.unshift({
                kind: "button",
                label: "立即重试",
                primary: true,
                onClick: async () => {
                  clearFeedbackActions();
                  setFeedbackState("running");
                  feedbackTitle.textContent = "正在重新发起任务";
                  feedbackDetail.textContent = "系统正在根据原始上传文件重试导入。";
                  feedbackStep.textContent = "重新进入处理队列";
                  feedbackProgressFill.style.width = "18%";
                  try {
                    const retryResponse = await window.fetch(String(jobPayload.retry_url), { method: "POST", headers: { Accept: "application/json" } });
                    if (!retryResponse.ok) {
                      throw new Error(await readErrorMessage(retryResponse));
                    }
                    const retryPayload = await retryResponse.json();
                    await pollAsyncJob(String(retryPayload.status_url || ""), String(retryPayload.redirect_url || redirectUrl || "/submissions"), inlineStep, pendingDetail);
                  } catch (retryError) {
                    setFeedbackState("error");
                    feedbackTitle.textContent = "重试失败";
                    feedbackDetail.textContent = retryError instanceof Error ? retryError.message : "任务重试失败，请稍后再试。";
                    feedbackStep.textContent = "重试未完成";
                    setFeedbackActions(actions);
                  }
                },
              });
            }
            setFeedbackActions(actions);
            restoreForm(form);
          }
        });
      }
    })();