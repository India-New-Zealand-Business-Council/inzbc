import { PLACEHOLDER_RESOURCES } from '../../lib/resourcesData'
import { DashboardCard } from './DashboardCard'

// Reuses the same data as the full ResourcesSection (not a re-declared copy) — see
// src/lib/resourcesData.ts. Shows the category shortcuts only, not the placeholder titles: this
// is meant as quick access to the resource types, not a preview of specific documents.
export function ResourcesWidget() {
  const categories = [...new Set(PLACEHOLDER_RESOURCES.map((resource) => resource.category))]

  return (
    <DashboardCard title="Resources" linkHref="#resources" linkLabel="View all resources">
      <ul className="space-y-2">
        {categories.map((category) => (
          <li key={category}>
            <a
              href="#resources"
              className="text-sm font-medium text-inzbc-navy underline decoration-inzbc-navy/30 underline-offset-2 hover:decoration-inzbc-navy focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inzbc-blue"
            >
              {category}
            </a>
          </li>
        ))}
      </ul>
    </DashboardCard>
  )
}
