import React, { useState, useEffect } from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Card, Button, Tag, Tooltip } from 'antd';
import { DeleteOutlined, CheckCircleOutlined, WarningOutlined, CloseCircleOutlined, LockOutlined } from '@ant-design/icons';

// Locked courses configuration
const LOCKED_COURSES = {
  "fall_1": ["CS1800", "CS2500", "MATH1341", "ENGW1111"],
  "spring_1": ["CS2510", "CS2800", "MATH1342", "DS2000"],
};

function isCourseLocked(courseId, year, semester) {
  // Add null check
  if (!semester) return false;
  const semesterKey = `${semester.toLowerCase()}_${year}`;
  return LOCKED_COURSES[semesterKey]?.includes(courseId) || false;
}

function DraggableCourse({ id, year, semester, onRemove, validation, isDragging = false }) {
  const [courseInfo, setCourseInfo] = useState(null);
  
  // Safely check if locked
  const isLocked = year && semester ? isCourseLocked(id, year, semester) : false;
  
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({ 
    id,
    disabled: isLocked // Disable dragging if course is locked
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    cursor: isLocked ? 'not-allowed' : 'grab',
    opacity: isDragging ? 0.5 : 1,
  };

  // Fetch course info on mount
 useEffect(() => {
    const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
    fetch(`${BACKEND_URL}/api/course_info/${id}`)
      .then(res => res.json())
      .then(data => setCourseInfo(data))
      .catch(err => console.error(err));
  }, [id]);

  // Check validation status for this course
  const courseErrors = validation?.errors?.filter(e => 
    e.type === 'missing_prerequisite' && e.message.includes(id)
  ) || [];
  
  const courseWarnings = validation?.warnings?.filter(w => 
    w.message.includes(id)
  ) || [];

  const hasError = courseErrors.length > 0;
  const hasWarning = courseWarnings.length > 0;

  const statusIcon = isLocked ?
    <LockOutlined style={{ color: '#faad14' }} /> :
    hasError ? 
    <CloseCircleOutlined style={{ color: '#ff4d4f' }} /> :
    hasWarning ?
    <WarningOutlined style={{ color: '#faad14' }} /> :
    <CheckCircleOutlined style={{ color: '#52c41a' }} />;

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <Card
        size="small"
        styles={{ body: { padding: '8px 12px' } }}
        style={{
          borderLeft: isLocked ? '4px solid #faad14' : hasError ? '4px solid #ff4d4f' : hasWarning ? '4px solid #faad14' : '4px solid #52c41a',
          backgroundColor: isLocked ? '#fffbe6' : 'white',
          marginBottom: '4px',
          opacity: isLocked ? 0.8 : 1,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ flex: 1 }}>
            <Tooltip title={isLocked ? `Required in ${semester?.charAt(0).toUpperCase() + semester?.slice(1)} Year ${year}` : courseInfo?.name || 'Loading...'}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {statusIcon}
                <strong>{id}</strong>
              </div>
            </Tooltip>
            {courseInfo && (
              <div style={{ fontSize: '11px', color: '#666', marginTop: '2px' }}>
                {courseInfo.credits || 4} credits • Complexity: {courseInfo.complexity || 5}/10
                {courseInfo.professors && courseInfo.professors.length > 0 && (
                  <div style={{ marginTop: '4px', fontSize: '10px', color: '#888', fontStyle: 'italic' }}>
                    Prof: {courseInfo.professors.slice(0, 2).join(', ')}
                    {courseInfo.professors.length > 2 && ` +${courseInfo.professors.length - 2}`}
                  </div>
                )}
              </div>
            )}
          </div>
          <Button
            type="text"
            size="small"
            danger
            disabled={isLocked}
            icon={<DeleteOutlined />}
            onClick={(e) => {
              e.stopPropagation();
              onRemove();
            }}
            title={isLocked ? "Cannot remove locked course" : "Remove course"}
          />
        </div>
        
        {isLocked && (
          <div style={{ marginTop: '8px', fontSize: '11px' }}>
            <Tag color="warning" icon={<LockOutlined />}>
              Required course - locked to {semester?.charAt(0).toUpperCase() + semester?.slice(1)} Year {year}
            </Tag>
          </div>
        )}

        {(hasError || hasWarning) && (
          <div style={{ marginTop: '8px', fontSize: '11px' }}>
            {courseErrors.map((err, i) => (
              <Tag key={i} color="error" style={{ marginBottom: '4px' }}>
                {err.message}
              </Tag>
            ))}
            {courseWarnings.map((warn, i) => (
              <Tag key={i} color="warning" style={{ marginBottom: '4px' }}>
                {warn.message}
              </Tag>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

export default DraggableCourse;
