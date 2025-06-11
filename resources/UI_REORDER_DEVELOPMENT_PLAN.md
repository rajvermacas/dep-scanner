# UI Reorder Development Plan

## Overview
This plan outlines the development of reordering UI sections in the dependency scanner HTML report with collapsible functionality.

## Current Structure vs Target Structure

### Current Order:
1. Languages
2. Package Managers  
3. Dependency Files
4. Dependencies
5. Categorized Dependencies and API Calls

### Target Order:
1. **Categorized Dependencies and API Calls** (Top Priority)
   - 1.1 Allowed Categories (collapsible)
     - Individual categories (Web Frameworks, etc.) - collapsible
   - 1.2 Restricted Categories (collapsible)
     - Individual categories - collapsible  
   - 1.3 Uncategorized/Cannot Determine (collapsible)
     - Individual categories - collapsible
2. Languages
3. Package Managers
4. Dependency Files
5. Dependencies (collapsible)

---

## Stage 1: HTML Template Structure Refactoring

### Objectives
- Modify HTML template to reorder sections
- Implement basic collapsible structure without JavaScript functionality
- Add visual indicators (arrows/icons) for collapsible sections

### Tasks
1. **Update HTML Reporter Template**
   - Modify `src/dependency_scanner_tool/reporters/templates/report.html`
   - Reorder sections according to target structure
   - Add collapsible container divs with appropriate CSS classes

2. **Add Collapsible CSS Classes**
   - Create `.collapsible-section` class for main sections
   - Create `.collapsible-header` class with arrow indicators
   - Create `.collapsible-content` class for content areas
   - Add `.collapsed` state classes
   - Implement smooth transition animations

3. **Update Section Headers**
   - Add arrow indicators (▼ expanded, ▶ collapsed)
   - Modify existing card headers to support collapsible functionality
   - Ensure proper semantic HTML structure

### Acceptance Criteria
- [ ] HTML template renders sections in correct order
- [ ] All collapsible sections have proper CSS classes applied
- [ ] Visual indicators (arrows) are present in section headers
- [ ] Default state shows all sections collapsed
- [ ] CSS transitions are smooth (0.3s duration)
- [ ] No JavaScript functionality required yet (CSS-only structure)
- [ ] Responsive design maintained across devices

### Files to Modify
- `src/dependency_scanner_tool/reporters/templates/report.html`
- CSS styles within the template file

### Estimated Time
2-3 hours

---

## Stage 2: JavaScript Collapsible Functionality

### Objectives
- Implement JavaScript toggle functionality for all collapsible sections
- Handle nested collapsible sections (categories within allowed/restricted groups)
- Ensure proper state management for expand/collapse

### Tasks
1. **Core Toggle Functionality**
   - Create `toggleSection(sectionId)` function
   - Handle arrow rotation (▼ ↔ ▶)
   - Manage content visibility with smooth animations
   - Store collapse/expand state in sessionStorage (optional)

2. **Nested Collapsible Logic**
   - Implement `toggleCategory(categoryId)` for individual categories
   - Handle parent-child relationships between main groups and categories
   - Ensure proper event delegation for dynamically generated content

3. **Event Listeners Setup**
   - Add click event listeners to collapsible headers
   - Prevent event bubbling issues with nested sections
   - Handle keyboard accessibility (Enter/Space key support)

4. **State Management**
   - Set default collapsed state on page load
   - Maintain consistent behavior across all sections
   - Handle edge cases (empty categories, missing data)

### Acceptance Criteria
- [ ] All main sections (Allowed, Restricted, Uncategorized, Dependencies) are collapsible
- [ ] Individual categories within groups are collapsible
- [ ] Arrow indicators rotate correctly (▼ when expanded, ▶ when collapsed)
- [ ] Smooth expand/collapse animations work consistently
- [ ] Default state: all sections collapsed on page load
- [ ] No JavaScript errors in browser console
- [ ] Keyboard accessibility supported (Enter/Space keys)
- [ ] Event handling works properly for nested sections
- [ ] Performance remains smooth with large datasets

### Files to Modify
- `src/dependency_scanner_tool/reporters/templates/report.html` (JavaScript section)

### Estimated Time
3-4 hours

---

## Stage 3: Data Reorganization and Backend Updates

### Objectives
- Modify HTML reporter to group categories by their status (allowed/restricted/cannot_determine)
- Update template rendering logic to support new nested structure
- Ensure data integrity and proper category grouping

### Tasks
1. **Update HTML Reporter Logic**
   - Modify `src/dependency_scanner_tool/reporters/html_reporter.py`
   - Group categorized dependencies by status before template rendering
   - Create helper functions for organizing data structure

2. **Template Data Structure Changes**
   - Update template context to include grouped categories
   - Modify template loops to render grouped structure
   - Ensure API calls and dependencies are properly nested under categories

3. **Category Status Grouping**
   - Create `group_categories_by_status()` function
   - Handle edge cases (categories without explicit status)
   - Maintain backward compatibility with existing data structure

4. **Template Rendering Updates**
   - Update Jinja2 template loops for new data structure
   - Ensure proper ID generation for collapsible elements
   - Maintain existing styling and functionality

### Acceptance Criteria
- [ ] Categories are properly grouped by status (allowed/restricted/cannot_determine)
- [ ] Each status group shows correct count of categories and items
- [ ] Individual categories within groups display dependencies and API calls
- [ ] Template renders without errors for various data scenarios
- [ ] Empty categories/groups are handled gracefully
- [ ] Existing functionality (search, filtering) remains intact
- [ ] Generated HTML IDs are unique and consistent
- [ ] Performance impact is minimal for large datasets
- [ ] All tests pass after modifications

### Files to Modify
- `src/dependency_scanner_tool/reporters/html_reporter.py`
- `src/dependency_scanner_tool/reporters/templates/report.html`

### Estimated Time
4-5 hours

---

## Implementation Notes

### CSS Classes Structure
```css
.collapsible-section {
  margin-bottom: 1.5rem;
}

.collapsible-header {
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.collapsible-arrow {
  transition: transform 0.3s ease;
}

.collapsible-arrow.collapsed {
  transform: rotate(-90deg);
}

.collapsible-content {
  max-height: 1000vh;
  overflow: hidden;
  transition: max-height 0.3s ease;
}

.collapsible-content.collapsed {
  max-height: 0;
}
```

### JavaScript Structure
```javascript
function toggleSection(sectionId) {
  const content = document.getElementById(sectionId);
  const arrow = document.querySelector(`[data-target="${sectionId}"] .collapsible-arrow`);
  
  content.classList.toggle('collapsed');
  arrow.classList.toggle('collapsed');
}
```

### Data Structure Changes
```python
# New grouped structure
grouped_categories = {
    'allowed': [
        {'name': 'Web Frameworks', 'dependencies': [...], 'api_calls': [...]},
        {'name': 'Data Science', 'dependencies': [...], 'api_calls': [...]}
    ],
    'restricted': [
        {'name': 'Machine Learning', 'dependencies': [...], 'api_calls': [...]}
    ],
    'cannot_determine': [
        {'name': 'Uncategorized', 'dependencies': [...], 'api_calls': [...]}
    ]
}
```

## Testing Strategy

### Unit Tests
- Test category grouping logic
- Test HTML template rendering with various data scenarios
- Test JavaScript functions in isolation

### Integration Tests
- Test complete HTML report generation
- Test collapsible functionality across different browsers
- Test responsive design on mobile devices

### Manual Testing
- Verify correct section ordering
- Test all collapsible functionality
- Verify visual indicators work correctly
- Test keyboard accessibility
- Verify performance with large datasets

## Risk Mitigation

### Potential Issues
1. **Performance**: Large datasets might cause slow animations
   - Solution: Implement virtual scrolling or pagination for large sections

2. **Browser Compatibility**: Older browsers might not support CSS transitions
   - Solution: Provide fallback styling for unsupported browsers

3. **Data Integrity**: Category grouping might fail with unexpected data
   - Solution: Implement robust error handling and fallbacks

4. **Accessibility**: Screen readers might have issues with collapsible content
   - Solution: Implement proper ARIA attributes and semantic HTML

## Total Estimated Time
9-12 hours across all three stages

## Success Criteria
The implementation will be considered successful when:
- All sections are reordered according to specifications
- All collapsible functionality works smoothly
- Default collapsed state is maintained
- Visual indicators work correctly
- Responsive design is preserved
- No performance degradation occurs
- All existing functionality remains intact