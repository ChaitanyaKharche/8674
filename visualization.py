import plotly.graph_objects as go
import json
from collections import defaultdict

def group_courses_by_levels(data):
    """Group courses into levels based on prerequisites."""
    levels = defaultdict(list)
    course_levels = {}

    for course in data:
        if not course['Prerequisites']:
            levels[1].append(course['Course ID'])
            course_levels[course['Course ID']] = 1
        else:
            prereq_levels = [
                course_levels.get(prereq.strip(), 0)
                for prereq in course['Prerequisites'].split(';')
                if prereq.strip()
            ]
            current_level = max(prereq_levels, default=0) + 1
            levels[current_level].append(course['Course ID'])
            course_levels[course['Course ID']] = current_level

    return levels, course_levels

def visualize_pathway(data):
    levels, course_levels = group_courses_by_levels(data)
    fig = go.Figure()

    x_positions = {}
    y_positions = {}
    max_courses_in_level = max(len(courses) for courses in levels.values())
    level_spacing = 2
    horizontal_spacing = 10 / max_courses_in_level  # Dynamic spacing

    for level, courses in levels.items():
        for idx, course_id in enumerate(courses):
            x_positions[course_id] = idx * horizontal_spacing  # Dynamic horizontal spacing
            y_positions[course_id] = level * level_spacing

    for course in data:
        prerequisites = course['Prerequisites'].split(';')
        for prereq in prerequisites:
            prereq = prereq.strip()
            if prereq in x_positions:
                fig.add_trace(go.Scatter(
                    x=[x_positions[prereq], x_positions[course['Course ID']]],
                    y=[y_positions[prereq], y_positions[course['Course ID']]],
                    mode='lines',
                    line=dict(width=1, dash='dot', color='blue'),
                    hoverinfo='none',  # No hover on lines
                    showlegend=False
                ))

        fig.add_trace(go.Scatter(
            x=[x_positions[course['Course ID']]],
            y=[y_positions[course['Course ID']]],
            mode='markers+text',
            marker=dict(size=12, color='red'),
            text=course['Course ID'],  # Static label with Course ID
            textposition='top center',
            hovertext=f"Course Name: {course['Course Name']}<br>Complexity: {course['Complexity_Metric']}<br>Prerequisites: {course['Prerequisites']}",
            hoverinfo='text',
            showlegend=False
        ))

    # Add background bands for levels
    for level in levels:
        fig.add_shape(
            type="rect",
            xref="paper",
            yref="y",
            x0=0,
            x1=1,
            y0=(level - 1) * level_spacing - 0.5,
            y1=level * level_spacing + 0.5,
            fillcolor="lightgray" if level % 2 == 0 else "white",
            opacity=0.2,
            layer="below",
            line_width=0,
        )

    # Update layout
    fig.update_layout(
        title='Enhanced Course Pathway Visualization',
        xaxis=dict(
            title='Courses',
            showgrid=False,
            zeroline=False,
            showticklabels=False
        ),
        yaxis=dict(
            title='Course Levels',
            tickmode='linear',
            tick0=0,
            dtick=level_spacing,
            showgrid=True,
            zeroline=False
        ),
        height=900,
        width=1200,
        showlegend=False
    )

    fig.show()

def main():
    with open('analyzed_degree_map.json') as f:
        data = json.load(f)
    visualize_pathway(data)

if __name__ == "__main__":
    main()
