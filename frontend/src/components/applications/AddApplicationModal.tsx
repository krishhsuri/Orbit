'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  X,
  Briefcase,
  Link2,
  MapPin,
  DollarSign,
  Tag,
  Star,
  Sparkles,
  ClipboardPaste,
  Loader2,
  ArrowLeft,
} from 'lucide-react';
import { useUIStore } from '@/stores';
import { useCreateApplication, useParseJobDescription } from '@/hooks/use-applications';
import type { ParsedJobDescription } from '@/lib/api';
import styles from './AddApplicationModal.module.css';

const sourceOptions = [
  'LinkedIn',
  'Direct',
  'Referral',
  'Career Fair',
  'Indeed',
  'Handshake',
  'Company Website',
  'Other',
];

const emptyForm = {
  company: '',
  role: '',
  url: '',
  source: 'Direct',
  location: '',
  salaryMin: '',
  salaryMax: '',
  priority: 3,
  tags: '',
  notes: '',
};

function draftToForm(draft: ParsedJobDescription) {
  const source =
    draft.source && sourceOptions.includes(draft.source) ? draft.source : 'Direct';

  let location = draft.location || '';
  if (draft.remote_type === 'hybrid' && location && !/hybrid/i.test(location)) {
    location = `${location} (Hybrid)`;
  } else if (draft.remote_type === 'onsite' && location && !/onsite|on-site|in.?office/i.test(location)) {
    location = `${location} (Onsite)`;
  }

  return {
    company: draft.company_name || '',
    role: draft.role_title || '',
    url: draft.job_url || '',
    source,
    location,
    salaryMin: draft.salary_min != null ? String(draft.salary_min) : '',
    salaryMax: draft.salary_max != null ? String(draft.salary_max) : '',
    priority: 3,
    tags: (draft.suggested_tags || []).join(', '),
    notes: draft.notes || '',
  };
}

export function AddApplicationModal() {
  const router = useRouter();
  const { isAddModalOpen, addModalMode, closeAddModal } = useUIStore();
  const createApplication = useCreateApplication();
  const parseJd = useParseJobDescription();

  const [mode, setMode] = useState<'form' | 'paste'>('form');
  const [pasteText, setPasteText] = useState('');
  const [parseHint, setParseHint] = useState<string | null>(null);
  const [formData, setFormData] = useState(emptyForm);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const filledFromPaste = useRef(false);

  useEffect(() => {
    if (isAddModalOpen) {
      setMode(addModalMode);
      if (addModalMode === 'paste') {
        filledFromPaste.current = false;
      }
    }
  }, [isAddModalOpen, addModalMode]);

  if (!isAddModalOpen) return null;

  const resetAndClose = () => {
    setFormData(emptyForm);
    setPasteText('');
    setParseHint(null);
    setMode('form');
    setErrors({});
    filledFromPaste.current = false;
    closeAddModal();
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  const handlePriorityChange = (priority: number) => {
    setFormData((prev) => ({ ...prev, priority }));
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.company.trim()) {
      newErrors.company = 'Company name is required';
    }
    if (!formData.role.trim()) {
      newErrors.role = 'Role is required';
    }
    if (formData.url && !formData.url.startsWith('http')) {
      newErrors.url = 'URL must start with http:// or https://';
    }
    if (formData.salaryMin && formData.salaryMax) {
      if (Number(formData.salaryMax) < Number(formData.salaryMin)) {
        newErrors.salaryMax = 'Max salary must be greater than min';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleParse = async () => {
    const text = pasteText.trim();
    if (text.length < 40) {
      setErrors({ paste: 'Paste a fuller job description (a few paragraphs is fine).' });
      return;
    }
    setErrors({});
    setParseHint(null);

    try {
      const result = await parseJd.mutateAsync(text);
      const draft = result.draft;
      if (!draft.company_name && !draft.role_title) {
        setErrors({
          paste: 'Couldn’t find a company or role in that paste. Try a cleaner section of the posting.',
        });
        return;
      }
      setFormData(draftToForm(draft));
      filledFromPaste.current = true;
      const bits: string[] = [];
      if (draft.confidence > 0) {
        bits.push(`${Math.round(draft.confidence * 100)}% confidence`);
      }
      if (result.truncated) bits.push('text was truncated');
      if (draft.salary_period === 'month') bits.push('stipend treated as monthly');
      setParseHint(bits.length ? `Filled from paste · ${bits.join(' · ')}` : 'Filled from paste — review before saving');
      setMode('form');
    } catch {
      setErrors({ paste: 'Failed to parse job description. Check your connection and try again.' });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) return;

    setIsSubmitting(true);

    try {
      const created = await createApplication.mutateAsync({
        company: formData.company.trim(),
        role: formData.role.trim(),
        source: formData.source,
        url: formData.url || undefined,
        location: formData.location || undefined,
        salaryMin: formData.salaryMin ? Number(formData.salaryMin) : undefined,
        salaryMax: formData.salaryMax ? Number(formData.salaryMax) : undefined,
        priority: formData.priority,
        notes: formData.notes || undefined,
        tags: formData.tags
          ? formData.tags
              .split(',')
              .map((t) => t.trim())
              .filter(Boolean)
          : [],
      });

      const goToKanban = filledFromPaste.current;
      resetAndClose();
      if (goToKanban) {
        router.push(`/kanban?highlight=${created.id}`);
      }
    } catch (error) {
      console.error('Failed to create application:', error);
      setErrors({ submit: 'Failed to create application. Please try again.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      resetAndClose();
    }
  };

  const busy = isSubmitting || parseJd.isPending;

  return (
    <div className={styles.backdrop} onClick={handleBackdropClick}>
      <div className={`${styles.modal} ${mode === 'paste' ? styles.modalWide : ''}`}>
        <div className={styles.header}>
          <div className={styles.headerTitle}>
            {mode === 'paste' && (
              <button
                type="button"
                className={styles.backButton}
                onClick={() => setMode('form')}
                disabled={busy}
                aria-label="Back to form"
              >
                <ArrowLeft size={16} />
              </button>
            )}
            <h2>{mode === 'paste' ? 'Paste job description' : 'Add Application'}</h2>
          </div>
          <button className={styles.closeButton} onClick={resetAndClose} type="button">
            <X size={20} />
          </button>
        </div>

        {mode === 'paste' ? (
          <div className={styles.pastePanel}>
            <p className={styles.pasteHelp}>
              Paste a LinkedIn post, careers page, internship blast, or apply-form page. We’ll
              extract company, role, location, pay, and a short notes summary — you review before
              saving.
            </p>
            <textarea
              className={`${styles.pasteArea} ${errors.paste ? styles.error : ''}`}
              value={pasteText}
              onChange={(e) => {
                setPasteText(e.target.value);
                if (errors.paste) setErrors((prev) => ({ ...prev, paste: '' }));
              }}
              placeholder="Paste the full posting here…"
              rows={14}
              disabled={busy}
              autoFocus
            />
            {errors.paste && <span className={styles.errorText}>{errors.paste}</span>}
            <div className={styles.actions}>
              <button
                type="button"
                className={styles.cancelButton}
                onClick={() => setMode('form')}
                disabled={busy}
              >
                Cancel
              </button>
              <button
                type="button"
                className={styles.submitButton}
                onClick={handleParse}
                disabled={busy || pasteText.trim().length < 40}
              >
                {parseJd.isPending ? (
                  <>
                    <Loader2 size={14} className={styles.spin} /> Parsing…
                  </>
                ) : (
                  <>
                    <Sparkles size={14} /> Fill form
                  </>
                )}
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className={styles.form}>
            {errors.submit && <div className={styles.submitError}>{errors.submit}</div>}
            {parseHint && <div className={styles.parseHint}>{parseHint}</div>}

            <button
              type="button"
              className={styles.pasteCta}
              onClick={() => setMode('paste')}
              disabled={busy}
            >
              <ClipboardPaste size={14} />
              <span>
                <strong>Paste a job description</strong>
                <em>LinkedIn, careers page, or internship blast → autofill</em>
              </span>
              <Sparkles size={14} />
            </button>

            <div className={styles.row}>
              <div className={styles.field}>
                <label htmlFor="company">
                  <Briefcase size={14} />
                  Company *
                </label>
                <input
                  type="text"
                  id="company"
                  name="company"
                  value={formData.company}
                  onChange={handleChange}
                  placeholder="e.g. Google"
                  className={errors.company ? styles.error : ''}
                  autoFocus
                  disabled={busy}
                />
                {errors.company && <span className={styles.errorText}>{errors.company}</span>}
              </div>

              <div className={styles.field}>
                <label htmlFor="role">Role *</label>
                <input
                  type="text"
                  id="role"
                  name="role"
                  value={formData.role}
                  onChange={handleChange}
                  placeholder="e.g. Software Engineer Intern"
                  className={errors.role ? styles.error : ''}
                  disabled={busy}
                />
                {errors.role && <span className={styles.errorText}>{errors.role}</span>}
              </div>
            </div>

            <div className={styles.row}>
              <div className={styles.field}>
                <label htmlFor="url">
                  <Link2 size={14} />
                  Job URL
                </label>
                <input
                  type="text"
                  id="url"
                  name="url"
                  value={formData.url}
                  onChange={handleChange}
                  placeholder="https://..."
                  className={errors.url ? styles.error : ''}
                  disabled={busy}
                />
                {errors.url && <span className={styles.errorText}>{errors.url}</span>}
              </div>

              <div className={styles.field}>
                <label htmlFor="source">Source</label>
                <select
                  id="source"
                  name="source"
                  value={formData.source}
                  onChange={handleChange}
                  disabled={busy}
                >
                  {sourceOptions.map((source) => (
                    <option key={source} value={source}>
                      {source}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className={styles.field}>
              <label htmlFor="location">
                <MapPin size={14} />
                Location
              </label>
              <input
                type="text"
                id="location"
                name="location"
                value={formData.location}
                onChange={handleChange}
                placeholder="e.g. San Francisco, CA or Remote"
                disabled={busy}
              />
            </div>

            <div className={styles.row}>
              <div className={styles.field}>
                <label htmlFor="salaryMin">
                  <DollarSign size={14} />
                  Salary Min
                </label>
                <input
                  type="number"
                  id="salaryMin"
                  name="salaryMin"
                  value={formData.salaryMin}
                  onChange={handleChange}
                  placeholder="e.g. 5000"
                  disabled={busy}
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="salaryMax">Salary Max</label>
                <input
                  type="number"
                  id="salaryMax"
                  name="salaryMax"
                  value={formData.salaryMax}
                  onChange={handleChange}
                  placeholder="e.g. 8000"
                  className={errors.salaryMax ? styles.error : ''}
                  disabled={busy}
                />
                {errors.salaryMax && <span className={styles.errorText}>{errors.salaryMax}</span>}
              </div>
            </div>

            <div className={styles.field}>
              <label>
                <Star size={14} />
                Priority
              </label>
              <div className={styles.priorityStars}>
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    className={`${styles.starButton} ${star <= formData.priority ? styles.active : ''}`}
                    onClick={() => handlePriorityChange(star)}
                    disabled={busy}
                  >
                    <Star size={20} />
                  </button>
                ))}
                <span className={styles.priorityLabel}>
                  {formData.priority === 1 && 'Low'}
                  {formData.priority === 2 && 'Below Average'}
                  {formData.priority === 3 && 'Medium'}
                  {formData.priority === 4 && 'High'}
                  {formData.priority === 5 && 'Top Priority'}
                </span>
              </div>
            </div>

            <div className={styles.field}>
              <label htmlFor="tags">
                <Tag size={14} />
                Tags
              </label>
              <input
                type="text"
                id="tags"
                name="tags"
                value={formData.tags}
                onChange={handleChange}
                placeholder="e.g. FAANG, Remote, Startup (comma separated)"
                disabled={busy}
              />
            </div>

            <div className={styles.field}>
              <label htmlFor="notes">Notes</label>
              <textarea
                id="notes"
                name="notes"
                value={formData.notes}
                onChange={handleChange}
                placeholder="Any additional notes..."
                rows={4}
                disabled={busy}
              />
            </div>

            <div className={styles.actions}>
              <button
                type="button"
                className={styles.cancelButton}
                onClick={resetAndClose}
                disabled={busy}
              >
                Cancel
              </button>
              <button type="submit" className={styles.submitButton} disabled={busy}>
                {isSubmitting ? 'Adding...' : 'Add Application'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
