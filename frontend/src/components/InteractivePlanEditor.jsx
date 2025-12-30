import React, { useState, useEffect } from 'react';
import { DndContext, DragOverlay, closestCenter, PointerSensor, useSensor, useSensors, useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { Card, Alert, Button, Space, Typography, Spin, message } from 'antd';
import { CheckCircleTwoTone } from '@ant-design/icons';
import DraggableCourse from './DraggableCourse';

const { Title, Text } = Typography;

// Droppable semester component
function DroppableSemester({ year, semester, courses, validation, onRemove }) {
  const semesterId = `semester_${year}_${semester}`;
  const { setNodeRef, isOver } = useDroppable({ id: semesterId });

  return (
    <div
      ref={setNodeRef}
      style={{
        minHeight: 150,
        padding: 12,
        border: isOver ? '3px solid #1890ff' : '2px dashed #d9d9d9',
        backgroundColor: isOver ? '#e6f7ff' : '#fafafa',
        borderRadius: 8,
        transition: 'all 0.2s ease',
      }}
    >
      <SortableContext items={courses} strategy={verticalListSortingStrategy}>
        {courses.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#999', padding: 20 }}>
            Drop courses here
          </div>
        ) : (
          <Space direction="vertical" style={{ width: '100%' }}>
            {courses.map(courseId => (
              <DraggableCourse
                key={courseId}
                id={courseId}
                year={year}
                semester={semester}
                validation={validation}
                onRemove={() => onRemove(courseId, year, semester)}
              />
            ))}
          </Space>
        )}
      </SortableContext>
    </div>
  );
}


function InteractivePlanEditor({ initialPlan, profile, track, onSave }) {
  const [plan, setPlan] = useState(initialPlan);
  const [activeId, setActiveId] = useState(null);
  const [validation, setValidation] = useState({ errors: [], warnings: [] });
  const [loading, setLoading] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    })
  );

  // Validate entire plan when plan changes
  useEffect(() => {
    validateEntirePlan();
  }, [plan]);

  const validateEntirePlan = async () => {
    try {
      const response = await fetch('/api/validate_entire_plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plan,
          completed_courses: profile.completed_courses || []
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        setValidation(result);
      }
    } catch (err) {
      console.error('Validation error:', err);
    }
  };
    
  const handleAddCourse = async (year, semester) => {
    // Get list of courses not in plan
    const usedCourses = new Set();

    // Handle different plan structures safely
    Object.keys(plan).forEach(yearKey => {
      if (!plan[yearKey] || typeof plan[yearKey] !== 'object') return;
      
      Object.keys(plan[yearKey]).forEach(sem => {
        const semesterCourses = plan[yearKey][sem];
        
        // Handle both array and non-array formats
        if (Array.isArray(semesterCourses)) {
          semesterCourses.forEach(c => usedCourses.add(c));
        } else if (typeof semesterCourses === 'string') {
          usedCourses.add(semesterCourses);
        }
      });
    });
      
    // Fetch available courses
    try {
      const response = await fetch('/api/courses');
      const data = await response.json();
      const allCourses = Object.keys(data.courses || {});
      const available = allCourses.filter(c => !usedCourses.has(c));
  
      // Show better selection UI
      const courseId = prompt(
        `Add course to ${semester.charAt(0).toUpperCase() + semester.slice(1)} Year ${year}:\n\n` +
        `Available courses:\n${available.slice(0, 20).join('\n')}\n\n` +
        `Enter course ID:`
      );
  
      if (!courseId) return;
      
      const trimmedId = courseId.trim().toUpperCase();
      
      if (!available.includes(trimmedId)) {
        message.error(`${trimmedId} is not available or already in plan`);
        return;
      }
  
      // Add to plan
      const yearKey = `year_${year}`;
      const updated = { ...plan };
      
      // Ensure year and semester exist
      if (!updated[yearKey]) updated[yearKey] = {};
      if (!Array.isArray(updated[yearKey][semester])) {
        updated[yearKey][semester] = [];
      }
      
      updated[yearKey][semester] = [...updated[yearKey][semester], trimmedId];
      setPlan(updated);
      message.success(`Added ${trimmedId} to ${semester} Year ${year}`);
    } catch (err) {
      console.error('Error in handleAddCourse:', err);
      message.error('Error adding course: ' + err.message);
    }
  };
    
  const handleDragStart = (event) => {
    setActiveId(event.active.id);
  };

  const handleDragEnd = async (event) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over) return;

    const courseId = active.id;
    
    // Parse target: "semester_1_fall" format
    const overParts = over.id.split('_');
    if (overParts.length < 3) return;
    
    const toYear = parseInt(overParts[1]);
    const toSemester = overParts[2];

    // Find current location
    let fromYear = null, fromSemester = null;
    
    for (let y = 1; y <= 4; y++) {
      const yearKey = `year_${y}`;
      if (!plan[yearKey]) continue;
      
      for (const sem of ['fall', 'spring']) {
        if (plan[yearKey][sem]?.includes(courseId)) {
          fromYear = y;
          fromSemester = sem;
          break;
        }
      }
      if (fromYear) break;
    }

    if (!fromYear || !fromSemester) {
      message.error('Could not find course location');
      return;
    }

    if (fromYear === toYear && fromSemester === toSemester) return;

    setLoading(true);
    try {
      const response = await fetch('/api/move_course', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plan: plan,
          course_id: courseId,
          from_semester: fromSemester,
          from_year: fromYear,
          to_semester: toSemester,
          to_year: toYear,
          completed_courses: profile.completed_courses || []
        })
      });

      if (!response.ok) {
        const error = await response.json();
        message.error(error.detail || 'Move failed');
        return;
      }

      const result = await response.json();
      setPlan(result.updated_plan);
      message.success(`Moved ${courseId} to ${toSemester} Year ${toYear}`);
    } catch (err) {
      message.error('Error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveCourse = (courseId, year, semester) => {
    const yearKey = `year_${year}`;
    const updated = { ...plan };
    updated[yearKey] = {
      ...updated[yearKey],
      [semester]: (updated[yearKey][semester] || []).filter(c => c !== courseId)
    };
    setPlan(updated);
    message.success(`Removed ${courseId}`);
  };

  if (!plan) return <Spin />;

  return (
    <Spin spinning={loading}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={3}>Interactive Planner - {track}</Title>
          <Button type="primary" onClick={() => onSave(plan)}>Save Plan</Button>
        </div>

        {validation.errors?.length > 0 && (
          <Alert
            type="error"
            message="Issues"
            description={validation.errors.map((e, i) => <div key={i}>{e.message}</div>)}
          />
        )}

        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '24px' }}>
            {[1, 2, 3, 4].map(year => (
              <Card key={`year_${year}`}>
                <Title level={4}>Year {year}</Title>
                <Space direction="vertical" style={{ width: '100%' }}>
                    {['fall', 'spring'].map(semester => {
                      const courses = plan[`year_${year}`]?.[semester] || [];
                      
                      return (
                        <div key={`${year}_${semester}`}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                            <Title level={5} style={{ margin: 0 }}>
                              {semester.charAt(0).toUpperCase() + semester.slice(1)}
                            </Title>
                            <Button 
                              type="dashed" 
                              size="small"
                              onClick={() => handleAddCourse(year, semester)}
                            >
                              + Add Course
                            </Button>
                          </div>
                          
                          <DroppableSemester
                            year={year}
                            semester={semester}
                            courses={courses}
                            validation={validation}
                            onRemove={handleRemoveCourse}
                          />
                        </div>
                      );
                    })}
                </Space>
              </Card>
            ))}
          </div>

          <DragOverlay>
            {activeId ? <Card style={{ width: 150, opacity: 0.5 }}>{activeId}</Card> : null}
          </DragOverlay>
        </DndContext>
      </Space>
    </Spin>
  );
}

export default InteractivePlanEditor;
