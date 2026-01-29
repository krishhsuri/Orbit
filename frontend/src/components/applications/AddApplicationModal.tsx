'use client';

import { useState } from 'react';
import { X, Briefcase, Link2, MapPin, DollarSign, Tag, Star } from 'lucide-react';
import { useUIStore } from '@/stores';
import { useCreateApplication } from '@/hooks';
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

export function AddApplicationModal() {
  const { isAddModalOpen, closeAddModal } = useUIStore();
  const createApplication = useCreateApplication();
  
  const [formData, setFormData] = useState({
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
  });
  
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isAddModalOpen) return null;

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear error when user types
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validate()) return;

    setIsSubmitting(true);

    try {
      await createApplication.mutateAsync({
        company: formData.company.trim(),
        role: formData.role.trim(),
        source: formData.source,
        url: formData.url || undefined,
        location: formData.location || undefined,
        salaryMin: formData.salaryMin ? Number(formData.salaryMin) : undefined,
        salaryMax: formData.salaryMax ? Number(formData.salaryMax) : undefined,
        priority: formData.priority,
        notes: formData.notes || undefined,
        tags: formData.tags ? formData.tags.split(',').map((t) => t.trim()).filter(Boolean) : [],
      });

      // Reset form and close
      setFormData({
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
      });
      closeAddModal();
    } catch (error) {
      console.error('Failed to create application:', error);
      setErrors({ submit: 'Failed to create application. Please try again.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      closeAddModal();
    }
  };

  return (
    <div className={styles.backdrop} onClick={handleBackdropClick}>
      <div className={styles.modal}>
        {/* Header */}
        <div className={styles.header}>
          <h2>Add Application</h2>
          <button className={styles.closeButton} onClick={closeAddModal}>
            <X size={20} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className={styles.form}>
          {errors.submit && (
            <div className={styles.submitError}>{errors.submit}</div>
          )}
          
          {/* Company & Role - Required */}
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
                disabled={isSubmitting}
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
                disabled={isSubmitting}
              />
              {errors.role && <span className={styles.errorText}>{errors.role}</span>}
            </div>
          </div>

          {/* URL & Source */}
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
                disabled={isSubmitting}
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
                disabled={isSubmitting}
              >
                {sourceOptions.map((source) => (
                  <option key={source} value={source}>{source}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Location */}
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
              disabled={isSubmitting}
            />
          </div>

          {/* Salary Range */}
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
                disabled={isSubmitting}
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
                disabled={isSubmitting}
              />
              {errors.salaryMax && <span className={styles.errorText}>{errors.salaryMax}</span>}
            </div>
          </div>

          {/* Priority */}
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
                  disabled={isSubmitting}
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

          {/* Tags */}
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
              disabled={isSubmitting}
            />
          </div>

          {/* Notes */}
          <div className={styles.field}>
            <label htmlFor="notes">Notes</label>
            <textarea
              id="notes"
              name="notes"
              value={formData.notes}
              onChange={handleChange}
              placeholder="Any additional notes..."
              rows={3}
              disabled={isSubmitting}
            />
          </div>

          {/* Actions */}
          <div className={styles.actions}>
            <button type="button" className={styles.cancelButton} onClick={closeAddModal} disabled={isSubmitting}>
              Cancel
            </button>
            <button type="submit" className={styles.submitButton} disabled={isSubmitting}>
              {isSubmitting ? 'Adding...' : 'Add Application'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
