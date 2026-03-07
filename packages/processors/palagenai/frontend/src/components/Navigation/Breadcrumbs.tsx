import React, { useMemo } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

interface Breadcrumb {
  label: string;
  path: string;
}

export const Breadcrumbs: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const params = useParams();

  const breadcrumbs = useMemo((): Breadcrumb[] => {
    const pathname = location.pathname;
    const pathSegments = pathname.split('/').filter(Boolean);

    if (pathSegments.length <= 1) {
      return [];
    }

    const crumbs: Breadcrumb[] = [];
    let currentPath = '';

    // Map route segments to readable labels
    const segmentLabels: Record<string, string> = {
      projects: 'Projects',
      bulk: 'Bulk OCR',
      archipelago: 'Archipelago',
      'archipelago-raw-uploader': 'Archipelago',
      workers: 'Workers',
      supervisor: 'Supervisor',
      swarm: 'Swarm Dashboard',
      'system-settings': 'Settings',
      images: 'Images',
    };

    pathSegments.forEach((segment, index) => {
      currentPath += `/${segment}`;

      // Skip dynamic route segments for now, handle them separately
      if (segment.match(/^[0-9a-f-]+$/i) && index > 0) {
        // This is likely a dynamic ID parameter
        const parentSegment = pathSegments[index - 1];
        const paramKey = parentSegment === 'projects' ? 'projectId' : parentSegment === 'images' ? 'imageId' : '';

        if (paramKey && params[paramKey as keyof typeof params]) {
          const paramValue = params[paramKey as keyof typeof params];
          const label = paramKey === 'projectId' ? `Project: ${paramValue?.substring(0, 8)}...` : `Image: ${paramValue?.substring(0, 8)}...`;
          crumbs.push({
            label,
            path: currentPath,
          });
        }
        return;
      }

      const label = segmentLabels[segment] || segment.charAt(0).toUpperCase() + segment.slice(1);
      crumbs.push({
        label,
        path: currentPath,
      });
    });

    return crumbs;
  }, [location.pathname, params]);

  if (breadcrumbs.length === 0) {
    return null;
  }

  return (
    <div className="bg-gradient-to-r from-slate-50 to-slate-100 border-b border-slate-200 px-6 py-2.5">
      <div className="max-w-7xl mx-auto">
        <nav className="flex items-center gap-0.5 text-sm">
          <button
            onClick={() => navigate('/projects')}
            className="px-3 py-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-200 rounded transition-all duration-150 font-medium flex items-center gap-1"
          >
            Home
          </button>

          {breadcrumbs.map((crumb, index) => (
            <React.Fragment key={crumb.path}>
              <span className="text-slate-400 mx-0.5">
                <ChevronRight className="w-4 h-4" />
              </span>
              {index === breadcrumbs.length - 1 ? (
                <span className="px-3 py-1.5 text-slate-900 font-semibold bg-slate-200 rounded flex items-center gap-1">
                  {crumb.label}
                </span>
              ) : (
                <button
                  onClick={() => navigate(crumb.path)}
                  className="px-3 py-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-200 rounded transition-all duration-150 font-medium flex items-center gap-1"
                >
                  {crumb.label}
                </button>
              )}
            </React.Fragment>
          ))}
        </nav>
      </div>
    </div>
  );
};

export default Breadcrumbs;
